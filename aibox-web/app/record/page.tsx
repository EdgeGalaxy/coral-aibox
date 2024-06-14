'use client'

import { useContext, useEffect, useState } from "react";

import { Collapse, CollapseProps } from "antd";
import { GlobalContext } from "@/components/api/context";

export default function RecordPage() {
  const baseUrl = useContext(GlobalContext).baseUrl
  const [ camerasRecords, setCamerasRecords] = useState<{ [key: string]: [] }>({});

  useEffect(() => {
    console.log('base url', baseUrl)
    fetch(`${baseUrl}/api/aibox_record/video/records`)
      .then((response) => response.json())
      .then((data) => {
        setCamerasRecords(data)
      })
  }, [baseUrl]);

  const videoRecorditems: CollapseProps["items"] = Object.keys(camerasRecords).map((key) => ({
    key: key,
    label: key,
    children: <div className="grid grid-cols-4 m-8">{camerasRecords[key].map((record) => (
      <div className="m-8" key={record}>
        <video controls src={`${baseUrl}/static/${record}`} key={record} />
        <p className="text-center">{record}</p>
      </div>
    ))}</div>
  }));


  return (
    <div className="mx-8 my-12">
      <p className="text-2xl font-bold mb-8">视频记录列表</p>
      <Collapse items={videoRecorditems} />
    </div>
  );

}
