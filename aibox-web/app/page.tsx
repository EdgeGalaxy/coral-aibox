"use client";

import { useState, useEffect } from "react";
import { Image, Select } from "antd";

import { AddCamera } from "@/components/addCamera";
import { DeleteCamera } from "@/components/deleteCamera";
import { getInternalHost } from "@/components/api/utils";
import { ActiveModal } from "@/components/activeModel";
import { ChangeResolution, LevelKeys } from "@/components/changeResolution";

const { Option } = Select;

export default function Home() {
  const [ loading, setLoading ] = useState(false);
  const [ baseUrl, setBaseUrl ] = useState("");
  const [cameras, SetCameras] = useState([]);
  const [prefixPath, setPrefixPath] = useState("8010/api/aibox_camera/cameras");
  const [ isActived, setIsActived ] = useState(true);
  const [ defaultLevel, setDefaultLevel ] = useState<LevelKeys>("origin");

  const selectItems = ["原视频", "推理视频"];

  const onChange = (value: string) => {
    if (value === "原视频") {
      setPrefixPath("8010/api/aibox_camera/cameras");
      fetch(`${baseUrl}:8030/api/aibox_face/cameras/stop_stream`)
        .then((response) => response.json())
        .then((data) => {
          console.log('inference camera data', data)
        })
    } else if (value === "推理视频") {
      setPrefixPath("8030/api/aibox_face/cameras");
      fetch(`${baseUrl}:8010/api/aibox_camera/cameras/stop_stream`)
        .then((response) => response.json())
        .then((data) => {
          console.log('origin camera data', data)
        })
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
    setLoading(true);
    fetch(`${baseUrl}:8010/api/aibox_camera/cameras`)
      .then((response) => response.json())
      .then((cameras) => SetCameras(cameras));
    
    fetch(`${baseUrl}:8010/api/aibox_camera/cameras/is_actived`)
      .then((response) => response.json())
      .then((isActived) => setIsActived(isActived));
    
    fetch(`${baseUrl}:8010/api/aibox_camera/cameras/resolution`)
      .then((response) => response.json())
      .then((level) => setDefaultLevel(level));
    setLoading(false);
  }, [baseUrl]);

  // if (loading) {
  //   return <div>Loading...</div>; // 显示加载状态
  // }

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
        <div className="mr-2">
          <DeleteCamera baseUrl={baseUrl} cameraIds={cameras} />
        </div>
        <div>
          <ChangeResolution baseUrl={baseUrl} defaultLevel={defaultLevel} />
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
                  {`${camera_id}-${defaultLevel}`}
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </>
  );
}
