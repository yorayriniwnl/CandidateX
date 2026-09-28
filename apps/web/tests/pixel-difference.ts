import type { Page } from '@playwright/test';

// Ignore subpixel GPU rounding, while detecting an actual change in the scene.
export async function changedPixels(page: Page, before: Buffer, after: Buffer): Promise<number> {
  return page.evaluate(async ([first, second]) => {
    async function decode(encoded: string) {
      const bytes = Uint8Array.from(atob(encoded), character => character.charCodeAt(0));
      const bitmap = await createImageBitmap(new Blob([bytes], { type: 'image/png' }));
      const surface = new OffscreenCanvas(bitmap.width, bitmap.height);
      const context = surface.getContext('2d')!;
      context.drawImage(bitmap, 0, 0);
      bitmap.close();
      return context.getImageData(0, 0, surface.width, surface.height);
    }
    const [a, b] = await Promise.all([decode(first), decode(second)]);
    if (a.width !== b.width || a.height !== b.height) return Math.max(a.width * a.height, b.width * b.height);
    let changed = 0;
    for (let i = 0; i < a.data.length; i += 4) {
      if ([0, 1, 2, 3].some(channel => Math.abs(a.data[i + channel] - b.data[i + channel]) > 2)) changed++;
    }
    return changed;
  }, [before.toString('base64'), after.toString('base64')]);
}
