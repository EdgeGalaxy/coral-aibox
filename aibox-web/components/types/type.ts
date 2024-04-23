


export interface ItemData {
    id: string;
    name: string;
    type: "folder" | "file";
    children?: ItemData[];
  }