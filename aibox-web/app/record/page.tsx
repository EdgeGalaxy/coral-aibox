"use client";

import { useContext, useEffect, useState } from "react";

import { Empty, Pagination, Select } from "antd";
import { GlobalContext } from "@/components/api/context";

const { Option } = Select;

export default function RecordPage() {
  const baseUrl = useContext(GlobalContext).baseUrl;
  const [cameraID, setCameraID] = useState<string>("");
  const [camerasRecords, setCamerasRecords] = useState<{ [key: string]: [] }>(
    {}
  );
  const [selectCameraRecords, setSelectCameraRecords] = useState<string[]>([]);
  const [crtPage, setCrtPage] = useState(1);
  const [crtPageSize, setCrtPageSize] = useState(8);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    setIsLoading(true);
    fetch(`${baseUrl}/api/aibox_record/video/records`)
      .then((response) => response.json())
      .then((data) => {
        if (data) {
          const defaultCameraID = Object.keys(data)[0];
          setCamerasRecords(data);
          setCameraID(defaultCameraID);
          setSelectCameraRecords(data[defaultCameraID].slice(0, crtPageSize));
        }
      })
      .finally(() => setIsLoading(false));
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

  if (isLoading) {
    return <div>Loading...</div>; // 显示加载状态
  }

  return (
    <>
      <div className="flex m-4 items-center">
        <p className="m-2 font-mono font-bold text-center">摄像头ID: </p>
        <Select
          className="text-center"
          defaultValue={Object.keys(camerasRecords)[1]}
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
              <video
                controls
                src={`${baseUrl}/api/aibox_record/static/${record}`}
                key={record}
              />
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
