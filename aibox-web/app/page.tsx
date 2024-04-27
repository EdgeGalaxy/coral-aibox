"use client";

import { useState, useEffect } from "react";
import { Image, Select } from "antd";

import { AddCamera } from "@/components/addCamera";
import { DeleteCamera } from "@/components/deleteCamera";
import { getInternalHost } from "@/components/api/utils";
import { ActiveModal } from "@/components/activeModel";

const { Option } = Select;

export default function Home() {
  const [ baseUrl, setBaseUrl ] = useState("");
  const [cameras, SetCameras] = useState([]);
  const [prefixPath, setPrefixPath] = useState("8010/api/aibox_camera/cameras");
  const [ isActived, setIsActived ] = useState(false);

  const selectItems = ["原视频", "推理视频"];

  const onChange = (value: string) => {
    if (value === "原视频") {
      setPrefixPath("8010/api/aibox_camera/cameras");
    } else if (value === "推理视频") {
      setPrefixPath("8030/api/aibox_face/cameras");
    }
  };
  useEffect(() => {
    const fetchInternalIP = async () => {
      const internalHost = await getInternalHost();
      console.log('internalHost', internalHost)
      setBaseUrl(internalHost)
      return internalHost
    }
    fetchInternalIP()
  }, []);

  useEffect(() => {
    fetch(`${baseUrl}:8010/api/aibox_camera/cameras`)
      .then((response) => response.json())
      .then((cameras) => SetCameras(cameras));
    
    fetch(`${baseUrl}:8010/api/aibox_camera/cameras/is_actived`)
      .then((response) => response.json())
      .then((isActived) => setIsActived(isActived));
  }, [baseUrl]);

  if (cameras.length === 0) {
    return <div>Loading...</div>; // 显示加载状态
  }

  return (
    <>
      <ActiveModal isOpen={!isActived} />
      <div className="flex m-4 items-center">
        <p className="mr-2 font-mono font-bold text-center">选择摄像头: </p>
        <Select
          className="text-center"
          defaultValue={selectItems[0]}
          style={{ width: 120, height: 40 }}
          onChange={onChange}
        >
          {selectItems.map((id) => (
            <Option key={id} value={id}>
              {id}
            </Option>
          ))}
        </Select>
      </div>
      <div className="flex my-8 mx-4 justify-end">
        <div className="mr-2">
          <AddCamera baseUrl={baseUrl}/>
        </div>
        <div>
          <DeleteCamera baseUrl={baseUrl} cameraIds={cameras} />
        </div>
      </div>
      <div className="grid grid-cols-2 gap-4">
        {cameras.map((camera_id: string) => {
          const videoUrl = `${baseUrl}:${prefixPath}/${camera_id}/stream`;
          return (
            <div className="mx-4" key={camera_id}>
              <Image
                key={camera_id}
                className="w-full"
                alt={camera_id}
                src={videoUrl}
              />
              <div className="flex justify-center">
                <p className="font-mono text-center text-base font-blod">
                  {camera_id}
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </>
  );
}
