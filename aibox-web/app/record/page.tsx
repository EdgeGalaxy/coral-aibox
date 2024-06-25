"use client";

import { useContext, useEffect, useState } from "react";
import LazyLoad from 'react-lazy-load';

import { Empty, Pagination, Select } from "antd";
import { GlobalContext } from "@/components/api/context";

const { Option } = Select;

type camerasRecordsType = {
  [key: string]: string[];
};

export default function RecordPage() {
  const baseUrl = useContext(GlobalContext).baseUrl;
  const [cameraID, setCameraID] = useState<string>("");
  const [camerasRecords, setCamerasRecords] = useState<camerasRecordsType>(
    {}
  );
  const [ selectTimeFile, setSelectTimeFile ] = useState<string>("");
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    setIsLoading(true);

    fetch(`${baseUrl}/api/aibox_record/video/records`)
      .then((response) => response.json())
      .then((data) => {
        if (data) {
          fetch(`${baseUrl}/api/aibox_camera/cameras`)
            .then((response) => response.json())
            .then((cameras) => {
              const usedCamerasRecords  = Object.entries(data).filter(([cameraID]) => cameras.includes(cameraID));
              const usedCamerasRecordsObj = Object.fromEntries(usedCamerasRecords) as camerasRecordsType
              const defaultCameraID = Object.keys(usedCamerasRecordsObj)[0];
              setCamerasRecords(usedCamerasRecordsObj);
              setCameraID(defaultCameraID);
              setSelectTimeFile(usedCamerasRecordsObj[defaultCameraID][0]);
          });
        }
      })

    setIsLoading(false);
  }, []);

  const onCameraChange = (cameraID: string) => {
    setCameraID(cameraID);
    setSelectTimeFile(camerasRecords[cameraID][0]);
  };

  const onTimeFileChange = (timeFile: string) => {
    setSelectTimeFile(timeFile);
  };


  if (isLoading || !cameraID ) {
    return <div>Loading...</div>; // 显示加载状态
  }

  return (
    <>
      <div className="flex m-4 items-center">
        <p className="m-2 font-mono font-bold text-center">摄像头ID: </p>
        <Select
          className="text-center"
          defaultValue={cameraID}
          style={{ width: 120, height: 40 }}
          onChange={onCameraChange}
        >
          {Object.keys(camerasRecords).map((id) => (
            <Option key={id} value={id}>
              {id}
            </Option>
          ))}
        </Select>

        <p className="m-2 font-mono font-bold text-center">时间段: </p>
        <Select
          defaultValue={camerasRecords[cameraID][0]}
          style={{ width: 300, height: 40 }}
          onChange={onTimeFileChange}
        >
          {camerasRecords[cameraID].map((file) => (
            <Option key={file} value={file}>
              {file}
            </Option>
          ))}
        </Select>
      </div>
      <div className="flex-col items-center justify-center h-screen">
        <LazyLoad>
          <video
            className="w-full h-auto"
            controls
            src={`${baseUrl}/api/aibox_record/static/${selectTimeFile}`}
          />
        </LazyLoad>
        <p className="text-center">{selectTimeFile}</p>
      </div>
    </>
  );
}
