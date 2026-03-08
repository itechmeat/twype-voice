import "@testing-library/jest-dom/vitest";

type StorageMap = Map<string, string>;

function createLocalStorage(): Storage {
  const storage = new Map<string, string>() as StorageMap;

  return {
    get length() {
      return storage.size;
    },
    clear() {
      storage.clear();
    },
    getItem(key) {
      return storage.get(key) ?? null;
    },
    key(index) {
      return Array.from(storage.keys())[index] ?? null;
    },
    removeItem(key) {
      storage.delete(key);
    },
    setItem(key, value) {
      storage.set(key, value);
    },
  };
}

Object.defineProperty(window, "localStorage", {
  configurable: true,
  value: createLocalStorage(),
});
