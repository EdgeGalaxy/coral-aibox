"use client";

import { useState, useEffect } from "react";
import { Image, Select } from "antd";

import { AddCamera } from "@/components/addCamera";
import { DeleteCamera } from "@/components/deleteCamera";
import { getInternalHost } from "@/components/api/utils";
import { ActiveModal } from "@/components/activeModel";
import { ChangeResolution, LevelKeys } from "@/components/changeResolution";
import { DownOutlined } from "@ant-design/icons";
import { ShowPerson } from "@/components/showPerson";

const { Option } = Select;
const MAX_COUNT = 4;

export default function Home() {
  const [ baseUrl, setBaseUrl ] = useState<string>("");
  const [ cameras, SetCameras ] = useState<string[]>([]);
  const [ selectCameras, setSelectCameras ] = useState<string[]>([]);
  const [ prefixPath, setPrefixPath ] = useState<string>("8030/api/aibox_face/cameras");
  const [ isActived, setIsActived ] = useState<boolean>(true);
  const [ defaultLevel, setDefaultLevel ] = useState<LevelKeys>("low");
  const [ wsUrl, setWsUrl ] = useState<string>("");

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

  const suffix = (
    <>
      <span>
        {selectCameras.length} / {MAX_COUNT}
      </span>
      <DownOutlined />
    </>
  );

  useEffect(() => {
    const fetchInternalIP = async () => {
      const internalHost = await getInternalHost();
      console.log('internalHost', internalHost)
      setBaseUrl(internalHost)
      const wsHost = internalHost.replace(/http/g, "ws")
      setWsUrl(`${wsHost}:8040/api/aibox_report/ws/person_count`)
      return internalHost
    }
    fetchInternalIP()
  }, []);

  useEffect(() => {
    fetch(`${baseUrl}:8010/api/aibox_camera/cameras`)
      .then((response) => response.json())
      .then((cameras) => {
        SetCameras(cameras)
        setSelectCameras(cameras.slice(0, MAX_COUNT))
    });
    
    fetch(`${baseUrl}:8010/api/aibox_camera/cameras/is_actived`)
      .then((response) => response.json())
      .then((isActived) => setIsActived(isActived));
    
    fetch(`${baseUrl}:8010/api/aibox_camera/cameras/resolution`)
      .then((response) => response.json())
      .then((level) => setDefaultLevel(level));
  }, [baseUrl]);

  if (wsUrl === "") {
    return <div>Loading...</div>; // 显示加载状态
  }

  return (
    <>
      <ActiveModal isOpen={!isActived} />
      <div className="flex m-4 items-center">
          <p className="m-2 font-mono font-bold text-center">选择视频类型: </p>
          <Select
            className="text-center"
            defaultValue={selectItems[1]}
            style={{ width: 120, height: 40 }}
            onChange={onChange}
          >
            {selectItems.map((id) => (
              <Option key={id} value={id}>
                {id}
              </Option>
            ))}
          </Select>
        <p className="m-2 font-mono font-bold text-center">选择摄像头(最多选{MAX_COUNT}个): </p>
          <Select
            mode="multiple"
            value={selectCameras}
            style={{ width: 120 * MAX_COUNT, height: 40 }}
            onChange={setSelectCameras}
            suffixIcon={suffix}
            maxCount={MAX_COUNT}
          >
            {cameras.map((id) => (
              <Option key={id} value={id}>
                {id}
              </Option>
            ))}
          </Select>

          <div>
            <ShowPerson wsUrl={wsUrl} />
          </div>
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
        {selectCameras.map((camera_id: string) => {
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
