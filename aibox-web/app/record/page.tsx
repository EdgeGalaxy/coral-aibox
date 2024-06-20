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
  const [selectCameraRecords, setSelectCameraRecords] = useState<string[]>([]);
  const [crtPage, setCrtPage] = useState(1);
  const [crtPageSize, setCrtPageSize] = useState(8);
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
              setSelectCameraRecords(usedCamerasRecordsObj[defaultCameraID]?.slice(0, crtPageSize));
          });
        }
      })

    setIsLoading(false);
  }, []);

  const onCameraChange = (cameraID: string) => {
    setCameraID(cameraID);
    setCrtPage(1);
    setSelectCameraRecords(camerasRecords[cameraID].slice(0, crtPageSize));
  };

  const onPageNumChange = (page: number, pageSize: number) => {
    setCrtPage(page);
    setCrtPageSize(pageSize);
    const index = (page - 1) * pageSize;
    setSelectCameraRecords(
      camerasRecords[cameraID].slice(index, index + pageSize)
    );
  };

  if (isLoading || !cameraID) {
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
      </div>

      {camerasRecords[cameraID]?.length > 0 ? (
        <div className="grid grid-cols-4 m-8">
          {selectCameraRecords.map((record) => (
            <div className="m-8" key={record}>
              <LazyLoad>
                <video
                  controls
                  src={`${baseUrl}/api/aibox_record/static/${record}`}
                  key={record}
                />
              </LazyLoad>
              <p className="text-center">{record}</p>
            </div>
          ))}
          :{" "}
        </div>
      ) : (
        <Empty
          className="content-center"
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        />
      )}
      <div className="mt-8 flex justify-center">
        <Pagination
          defaultCurrent={crtPage}
          defaultPageSize={crtPageSize}
          hideOnSinglePage
          total={camerasRecords[cameraID]?.length}
          onChange={onPageNumChange}
        />
      </div>
    </>
  );
}
