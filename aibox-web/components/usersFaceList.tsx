import React, { useState, useEffect, memo } from "react";
import { List, Menu, Dropdown, message, Input, MenuProps } from "antd";
import { FileOutlined } from "@ant-design/icons";

import { ItemData } from "./types/type";
import { Folder } from "./folder";

interface RenameState {
  id: string | null;
  name: string;
  oldName: string;
}

const _UsersFaceList = ({
  baseUrl,
  data,
}: {
  baseUrl: string;
  data: ItemData[];
}) => {
  const [usersData, setUsersData] = useState<ItemData[]>([]);
  const [renameState, setRenameState] = useState<RenameState>({
    id: null,
    name: "",
    oldName: "",
  });
  const [contextMenu, setContextMenu] = useState<{
    visible: boolean;
    x: number;
    y: number;
    item: ItemData | null;
  }>({ visible: false, x: 0, y: 0, item: null });

  useEffect(() => {
    setUsersData(data);
  }, [data]);

  const handleContextMenu = (item: ItemData, event: React.MouseEvent) => {
    event.preventDefault();
    setContextMenu({
      visible: true,
      x: event.clientX,
      y: event.clientY,
      item,
    });
  };

  const handleMenuClick = (e: any) => {
    if (e.key === "rename") {
      setRenameState({
        id: contextMenu.item?.id || "",
        name: contextMenu.item?.name || "",
        oldName: contextMenu.item?.name || "",
      });
      setContextMenu({ ...contextMenu, visible: false });
    } else if (e.key === "delete") {
      setUsersData(
        usersData.filter((item) => item.name !== contextMenu.item?.name)
      );
      handleDelete();
      setContextMenu({ ...contextMenu, visible: false });
    }
  };

  const handleDelete = () => {
    fetch(
      `${baseUrl}:8030/api/aibox_face/users/${contextMenu.item?.name}/faces`,
      {
        method: "DELETE",
      }
    )
      .then((response) => {
        if (response.ok) {
          message.success("删除成功");
        } else {
          message.error("删除失败");
        }
      })
      .catch((error) => {
        message.error("删除失败");
      });
  };

  const handleRename = async () => {
    const renameUrl = `${baseUrl}:8030/api/aibox_face/users/remark`;
    fetch(renameUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        remark_user_id: renameState.name,
        old_user_id: renameState.oldName,
      }),
    })
      .then((response) => {
        // 更新
        setUsersData(
          usersData.map((item) =>
            item.id === renameState.id
              ? { ...item, name: renameState.name }
              : item
          )
        );
        setRenameState({
          id: null,
          name: renameState.name,
          oldName: renameState.name,
        });
        message.success("重命名成功");
      })
      .catch((error) => {
        setUsersData(
          usersData.map((item) =>
            item.id === renameState.id
              ? { ...item, name: renameState.oldName }
              : item
          )
        );
        setRenameState({
          id: null,
          name: renameState.oldName,
          oldName: renameState.oldName,
        });
        message.error("重命名失败");
      });
  };

  const handleOutsideClick = (e: MouseEvent) => {
    if (contextMenu.visible) setContextMenu({ ...contextMenu, visible: false });
  };

  useEffect(() => {
    document.addEventListener("click", handleOutsideClick);
    return () => {
      document.removeEventListener("click", handleOutsideClick);
    };
  });

  const menu: MenuProps = {
    onClick: handleMenuClick,
    items: [
      {
        key: "rename",
        label: "重命名",
        title: "重命名",
      },
      {
        key: "delete",
        label: "删除",
        title: "删除",
      }
    ]
  }

  return (
    <>
      {contextMenu.visible && (
        <div
          style={{
            position: "fixed",
            left: `${contextMenu.x}px`,
            top: `${contextMenu.y}px`,
          }}
        >
          <Dropdown menu={menu} open={true}>
            <div />
          </Dropdown>
        </div>
      )}
      <List
        className="m-12"
        itemLayout="horizontal"
        dataSource={usersData}
        renderItem={(item) => (
          <List.Item onContextMenu={(event) => handleContextMenu(item, event)}>
            <List.Item.Meta
              title={
                renameState.id === item.id ? (
                  <Input
                    value={renameState.name}
                    onChange={(e) =>
                      setRenameState({ ...renameState, name: e.target.value })
                    }
                    onPressEnter={handleRename}
                    onBlur={handleRename}
                  />
                ) : item.type == "folder" ? (
                  <Folder
                    baseUrl={baseUrl}
                    folder={item}
                    usersData={usersData}
                    setUsersData={setUsersData}
                  />
                ) : (
                  <>
                    <FileOutlined /> {item.name}
                  </>
                )
              }
            />
          </List.Item>
        )}
      />
    </>
  );
};

export const UsersFaceFolderList = memo(_UsersFaceList);
