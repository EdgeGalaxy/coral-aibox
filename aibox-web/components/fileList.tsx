import React, {
  Dispatch,
  SetStateAction,
  memo,
  useEffect,
  useState,
} from "react";
import {
  List,
  Dropdown,
  message,
  Avatar,
  Modal,
  MenuProps,
  Select,
} from "antd";

import { ItemData } from "./types/type";

type FileListProps = {
  baseUrl: string;
  folderID: string;
  files: ItemData[];
  usersData: ItemData[];
  setUsersData: Dispatch<SetStateAction<ItemData[]>>;
};

const _FileList = ({
  baseUrl,
  folderID,
  files: items,
  usersData,
  setUsersData,
}: FileListProps) => {
  const [childrenMenu, setChildrenMenu] = useState<{
    visible: boolean;
    x: number;
    y: number;
    item: ItemData | null;
  }>({ visible: false, x: 0, y: 0, item: null });
  const [avatarModalVisable, setAvatarModalVisable] = useState(false);
  const [moveVisable, setMoveVisable] = useState(false);
  const [moveFolderID, setMoveFolderID] = useState("");
  const [facePreview, setFacePreview] = useState("");

  const handleChildMenu = (item: ItemData, event: React.MouseEvent) => {
    event.preventDefault();
    setChildrenMenu({
      visible: true,
      x: event.clientX,
      y: event.clientY,
      item,
    });
  };

  const handleChildrenDelete = () => {
    fetch(
      `${baseUrl}/api/aibox_face/users/${folderID}/faces/${childrenMenu.item?.name}`,
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

  const handleChildrenMenuClick = (e: any) => {
    if (e.key === "delete") {
      setUsersData(
        usersData.filter((item) => {
          if (item.children) {
            item.children = item.children?.filter(
              (child) => child.name != childrenMenu.item?.name
            );
            if (item.children?.length == 0) {
              return false;
            }
          }
          return item;
        })
      );
      handleChildrenDelete();
      setChildrenMenu({ ...childrenMenu, visible: false });
    } else if (e.key == "move") {
      setMoveVisable(true);
    }
  };

  const handleAvatarClick = (faceID: string) => {
    setAvatarModalVisable(true);
    setFacePreview(`${baseUrl}/api/aibox_face/static/${folderID}/${faceID}.jpg`);
  };

  const handleSelectChange = (destFolderID: string) => {
    setMoveFolderID(destFolderID);
  };

  const handleConfirmMove = (faceID: string) => {
    fetch(
      `${baseUrl}/api/aibox_face/users/${folderID}/move/${moveFolderID}`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          face: faceID,
        }),
      }
    )
      .then((response) => {
        if (response.ok) {
          message.success("移动成功");
          setUsersData(
            usersData.filter((item) => {
              if (item.name == folderID) {
                if (item.children) {
                  item.children = item.children.filter(
                    (child) => child.name != faceID
                  );
                }
                if (item.children?.length == 0) {
                  return false;
                }
              } else if (item.name == moveFolderID) {
                const moveItemData: ItemData = {
                  name: faceID,
                  children: [],
                  type: "file",
                  id: faceID,
                };
                if (item.children) {
                  item.children.push(moveItemData);
                } else {
                  item.children = [moveItemData];
                }
              }
              return item;
            })
          );
        } else {
          message.error("移动失败");
        }
      })
      .catch((error) => {
        message.error("移动失败");
      })
      .finally(() => {
        setMoveVisable(false);
      });
  };

  const handleOutsideClick = (e: MouseEvent) => {
    if (childrenMenu.visible)
      setChildrenMenu({ ...childrenMenu, visible: false });
  };

  useEffect(() => {
    document.addEventListener("click", handleOutsideClick);
    return () => {
      document.removeEventListener("click", handleOutsideClick);
    };
  });

  const childMenus: MenuProps = {
    onClick: handleChildrenMenuClick,
    items: [
      {
        key: "delete",
        label: "删除",
        title: "删除",
      },
      {
        key: "move",
        label: "移动",
        title: "移动",
      },
    ],
  };

  // 过滤掉自身folder
  const selectOptions = usersData
    .filter((item) => (item.name != folderID && !item.name.startsWith('UNKNOWN')))
    .map((item) => {
      return {
        label: item.name,
        value: item.name,
      };
    });

  return (
    <>
      {childrenMenu.visible && (
        <div
          style={{
            position: "fixed",
            left: `${childrenMenu.x}px`,
            top: `${childrenMenu.y}px`,
          }}
        >
          <Dropdown menu={childMenus} open={true}>
            <div />
          </Dropdown>
        </div>
      )}
      <List
        size="small"
        bordered
        dataSource={items}
        renderItem={(item) => (
          <List.Item onContextMenu={(event) => handleChildMenu(item, event)}>
            <List.Item.Meta
              avatar={
                <Avatar
                  src={`${baseUrl}/api/aibox_face/static/${folderID}/${item.name}.jpg`}
                  onClick={() => handleAvatarClick(item.name)}
                />
              }
              title={item.name}
            />
            <Modal
              className="w-1/3"
              open={moveVisable}
              onCancel={() => setMoveVisable(false)}
              onOk={() => handleConfirmMove(item.name)}
              title="移动文件"
            >
              <Select
                className="w-full my-8"
                placeholder="选择移动的文件夹"
                onChange={handleSelectChange}
                options={selectOptions}
              />
            </Modal>
            <Modal
            open={avatarModalVisable}
            onCancel={() => setAvatarModalVisable(false)}
            footer={null}
            >
            <img
            src={facePreview}
            style={{ width: "100%" }}
            alt="大图"
            />
            </Modal>
          </List.Item>
        )}
      />
    </>
  );
};

export const FileList = memo(_FileList);
