/** Synchronize caption fields using the merchant's already signed-in Teeinblue editor. */
export async function syncOpenCampaign(tab, {handle, campaignPath, shopHosts, plan, matches = {}, write = false}) {
  const url = new URL(await tab.url());
  if (url.hostname !== 'portal.teeinblue.com' || !/^\/campaigns\/\d+\/edit$/.test(campaignPath) || url.pathname !== campaignPath) {
    throw new Error('Open the verified campaign editor first.');
  }
  if (!/^[-a-z0-9]+$/.test(handle) || !shopHosts.length || !plan?.images || !plan.by_previous_caption) {
    throw new Error('A verified Shopify product and its caption plan are required.');
  }
  const page = tab.playwright;
  const cards = page.locator('li.campaign-available-product');
  await cards.first().waitFor({state: 'visible', timeoutMs: 25000});
  const destinations = await page.evaluate(() => [...document.querySelectorAll('a[href]')].map(a => a.href));
  const linked = destinations.some(href => {
    const link = new URL(href);
    return link.protocol === 'https:' && shopHosts.includes(link.hostname) && link.pathname === '/products/' + handle;
  });
  if (!linked) throw new Error('The campaign does not link to the intended Shopify product.');

  const bases = await page.evaluate(() => [...document.querySelectorAll('li.campaign-available-product')].map(card => ({
    path: card.querySelector('a[title="Go to product base"]')?.getAttribute('href'),
    name: card.querySelector('.campaign-available-product-title')?.textContent.trim()
  })));
  async function readGallery(base) {
    if (!/^\/products\/\d+\/edit$/.test(base.path) || !base.name) throw new Error('Invalid product base.');
    const baseLink = page.locator('a[href=' + JSON.stringify(base.path) + ']');
    const row = cards.filter({has: baseLink});
    if (await row.count() !== 1) throw new Error('Ambiguous product base.');
    const alreadySelected = await page.evaluate(path => [...document.querySelectorAll('li.campaign-available-product')]
      .some(card => card.matches('.selected,.active') && card.querySelector('a[title="Go to product base"]')?.getAttribute('href') === path), base.path);
    if (!alreadySelected) await row.locator('.campaign-available-product-title').click({timeoutMs: 16000});
    const deadline = Date.now() + 20000;
    do {
      const view = await page.evaluate(() => {
        const choices = [...document.querySelectorAll('li.campaign-available-product')];
        const selected = choices.filter(li => li.matches('.selected,.active'))
          .map(li => li.querySelector('a[title="Go to product base"]')?.getAttribute('href'));
        const title = [...document.querySelectorAll('strong')]
          .find(el => el.previousSibling?.textContent.includes('Print Areas of'))?.textContent.trim();
        const gallery = [...document.querySelectorAll('li.campaign-gallery-thumbnail')];
        const images = gallery.map(li => {
          const image = [...li.querySelectorAll('img')].find(img => img.src.startsWith('https://cdn.teeinblue.com/') && !img.src.endsWith('/loading.svg'));
          return image ? {id: li.title, file: image.src, alt: image.alt} : null;
        });
        const unavailable = [...document.querySelectorAll('a')].filter(a =>
          a.textContent.trim() === 'Product Base' &&
          a.parentElement?.innerText.trim() === 'No variant for this product. Go to Product Base to add a variant.'
        ).map(a => a.getAttribute('href'));
        return {selected, title, images, unavailable};
      });
      const current = view.selected.length === 1
        ? view.selected[0] === base.path && (!view.title || view.title === base.name)
        : view.title === base.name;
      if (!current) continue;
      if (!view.images.length && view.unavailable.includes(base.path)) return [];
      if (view.images.length && view.images.every(im => im && /^#\d+$/.test(im.id)) &&
          new Set(view.images.map(im => im.id)).size === view.images.length) return view.images;
    } while (Date.now() < deadline);
    throw new Error('The selected base gallery could not be verified: ' + base.name);
  }

  async function saveCaption(image, caption) {
    const card = page.locator('li.campaign-gallery-thumbnail[title=' + JSON.stringify(image.id) + ']')
      .filter({has: page.locator('img[src=' + JSON.stringify(image.file) + ']')});
    if (await card.count() !== 1) throw new Error('The source mockup has changed.');
    const editor = card.getByRole('button', {name: /^Edit .*/});
    const altButton = page.getByRole('button', {name: /Alt text/});
    await editor.click({timeoutMs: 16000});
    try {
      await altButton.waitFor({state: 'visible', timeoutMs: 8000});
    } catch (error) {
      if (await editor.count() !== 1 || await altButton.count()) throw error;
      await editor.press('Enter');
    }
    await altButton.click({timeoutMs: 16000});
    const box = page.getByRole('dialog').getByRole('textbox', {name: '', exact: true});
    await box.waitFor({state: 'visible', timeoutMs: 16000});
    async function observed() {
      const values = await page.evaluate(() => [...document.querySelectorAll('[role=dialog] input[type=text]')]
        .filter(input => input.getClientRects().length).map(input => input.value));
      if (values.length !== 1) throw new Error('The caption editor has changed.');
      return values[0];
    }
    const deadline = Date.now() + 13000;
    let previous = await observed();
    while (!previous && image.alt && Date.now() < deadline) previous = await observed();
    if (previous !== image.alt) throw new Error('The original caption has changed.');
    await box.fill(caption);
    await box.press('Tab');
    if (await observed() !== caption) throw new Error('The editor did not retain the approved caption.');
    await page.getByRole('button', {name: 'Save', exact: true}).click();
    await box.waitFor({state: 'hidden', timeoutMs: 16000});
    const finish = page.getByRole('button', {name: 'Save & Close', exact: true});
    await finish.press('Enter');
    try {
      await finish.waitFor({state: 'hidden', timeoutMs: 18000});
    } catch (error) {
      const pending = await page.evaluate(() => [...document.querySelectorAll('button')]
        .filter(button => button.textContent.trim() === 'Save & Close' && button.getClientRects().length)
        .map(button => button.disabled));
      if (!pending.length) return;
      if (pending.length !== 1) throw error;
      if (!pending[0]) await finish.press('Enter');
      await finish.waitFor({state: 'hidden', timeoutMs: 65000});
    }
  }

  const actions = [], unresolved = [], confirmed = [], emptyBases = [];
  const desired = new Set(Object.values(plan.images).map(image => image.caption));
  for (const base of bases) {
    const photos = await readGallery(base);
    if (!photos.length) emptyBases.push(base.path);
    for (const image of photos) {
      const match = matches[base.path]?.[image.id];
      const approved = match && plan.images[match.shopifyUrl];
      if (match && (!approved || match.sourceUrl !== image.file || ![approved.previous, approved.caption].includes(image.alt))) {
        throw new Error('The pre-verified source mockup or its Shopify image changed.');
      }
      const caption = approved?.caption ?? plan.by_previous_caption[image.alt];
      const item = {base: base.path, id: image.id, sourceUrl: image.file, previous: image.alt};
      if (!caption || caption === image.alt) {
        if (desired.has(image.alt)) confirmed.push({...item, caption: image.alt});
        else unresolved.push(item);
        continue;
      }
      if (!desired.has(caption)) throw new Error('The destination caption is outside the approved plan.');
      actions.push({...item, caption});
      if (write) await saveCaption(image, caption);
    }
  }
  if (write && actions.length) {
    await tab.reload();
    await cards.first().waitFor({state: 'visible', timeoutMs: 25000});
    for (const base of bases) {
      const updates = actions.filter(item => item.base === base.path);
      if (!updates.length) continue;
      const photos = await readGallery(base);
      for (const item of updates) {
        if (!photos.some(im => im.id === item.id && im.file === item.sourceUrl && im.alt === item.caption)) {
          throw new Error('The saved source caption could not be verified: ' + item.id);
        }
        confirmed.push(item);
      }
    }
  }
  return {handle, campaignPath, write, actions, confirmed, unresolved, emptyBases};
}
