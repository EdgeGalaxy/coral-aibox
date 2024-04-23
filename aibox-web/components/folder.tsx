import React, { Dispatch, SetStateAction, memo } from "react";
import { Collapse } from "antd";
import { FolderOutlined, FileOutlined } from "@ant-design/icons";

import { ItemData } from "./types/type";
import { FileList } from "./fileList";

type FolderProps = {
  baseUrl: string;
  folder: ItemData;
  usersData: ItemData[];
  setUsersData: Dispatch<SetStateAction<ItemData[]>>;
};

const _Folder = ({ baseUrl, folder, usersData, setUsersData }: FolderProps) => {
  return (
    <Collapse
      bordered={false}
      items={[
        {
          key: folder.id,
          label: (
            <div style={{ display: "flex", alignItems: "center" }}>
              <FolderOutlined />
              {folder.name}
            </div>
          ),
          children: (
            <FileList
              baseUrl={baseUrl}
              folderID={folder.name}
              files={folder.children || []}
              usersData={usersData}
              setUsersData={setUsersData}
            />
          ),
        },
      ]}
    />
  );
};

export const Folder = memo(_Folder);
