"use client";

import { CameraMask } from "@/components/cameraMask";
import { useEffect, useState } from "react";
import { Select } from "antd";
import { getInternalHost } from "@/components/api/utils";

const { Option } = Select;

export default function Configuration() {
  const BASE_URL = getInternalHost();
  const [cameras, setCameras] = useState([]);
  const [selectCameraID, setSelectCameraID] = useState<string>("");

  useEffect(() => {
    fetch(`${BASE_URL}:8010/api/aibox_camera/cameras`)
      .then((response) => response.json())
      .then((cameras) => {
        setCameras(cameras);
        setSelectCameraID(cameras[0]);
      });
  }, []);

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
        >
          {cameras.map((id) => (
            <Option key={id} value={id}>
              {id}
            </Option>
          ))}
        </Select>
      </div>
      <div className="grid grid-cols-1">
        <CameraMask camera_id={selectCameraID} />
      </div>
    </div>
  );
}
