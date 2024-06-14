"use client";

import { CameraMask } from "@/components/cameraMask";
import { useContext, useEffect, useState } from "react";
import { Select } from "antd";
import { GlobalContext } from "@/components/api/context";

const { Option } = Select;

export default function Configuration() {
  const baseUrl = useContext(GlobalContext).baseUrl
  const [cameras, setCameras] = useState([]);
  const [selectCameraID, setSelectCameraID] = useState<string>("");

  useEffect(() => {
    fetch(`${baseUrl}/api/aibox_camera/cameras`)
      .then((response) => response.json())
      .then((cameras) => {
        setCameras(cameras);
        setSelectCameraID(cameras[0]);
      });
  }, [baseUrl]);

  const onSelectChange = (value: string) => {
    console.log('selectCameraID', value)
    setSelectCameraID(value);
  }

  if (cameras.length === 0 || selectCameraID === "") {
    return <div>Loading...</div>; // 显示加载状态
  }

  return (
    <div>
      <div className="flex m-4 items-center">
        <p className="mr-2 font-mono font-bold text-center">选择摄像头: </p>
        <Select
          className="text-center"
          defaultValue={selectCameraID}
          style={{ width: 120, height: 40 }}
          onChange={onSelectChange}
        >
          {cameras.map((id) => (
            <Option key={id} value={id}>
              {id}
            </Option>
          ))}
        </Select>
      </div>
      <CameraMask camera_id={selectCameraID} baseUrl={baseUrl} />
    </div>
  );
}
