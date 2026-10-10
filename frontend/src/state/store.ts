import { create } from 'zustand'

type Store = {
  selectedObjectId?: string
  selectedEncounterId?: string
  setSelectedObject: (id?: string) => void
  setSelectedEncounter: (id?: string) => void
}

export const useKesslerStore = create<Store>(set => ({
  setSelectedObject: selectedObjectId => set({ selectedObjectId }),
  setSelectedEncounter: selectedEncounterId => set({ selectedEncounterId }),
}))
