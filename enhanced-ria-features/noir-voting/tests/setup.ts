/**
 * Jest setup file for Noir ZKP integration tests
 */

global.console = {
  ...console,
  log: () => {},
  debug: () => {},
  info: () => {},
  warn: console.warn,
  error: console.error,
};

(global as any).TextEncoder = class TextEncoder {
  encode(input: string): Uint8Array {
    return new Uint8Array(Buffer.from(input, 'utf-8'));
  }
};

(global as any).TextDecoder = class TextDecoder {
  decode(input: Uint8Array): string {
    return Buffer.from(input).toString('utf-8');
  }
};

if (typeof Buffer === 'undefined') {
  global.Buffer = {
    from: (data: string | number[], encoding?: string) => {
      if (typeof data === 'string') {
        return new Uint8Array(data.split('').map(c => c.charCodeAt(0)));
      }
      return new Uint8Array(data);
    }
  } as any;
}


global.performance = {
  now: () => Date.now(),
  mark: () => {},
  measure: () => {},
  getEntriesByName: () => [],
  getEntriesByType: () => [],
  clearMarks: () => {},
  clearMeasures: () => {}
} as any;
