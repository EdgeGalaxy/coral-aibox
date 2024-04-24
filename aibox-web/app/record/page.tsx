'use client'

import { useEffect, useState } from "react";


import { getInternalHost } from "@/components/api/utils";
import { Collapse, CollapseProps } from "antd";

export default function RecordPage() {
  const [ baseUrl, setBaseUrl ] = useState("");
  const [ camerasRecords, setCamerasRecords] = useState<{ [key: string]: [] }>({});

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
    console.log('base url', baseUrl)
    fetch(`${baseUrl}:8050/api/aibox_record/video/records`)
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
        <video controls src={`${baseUrl}:8050/static/${record}`} key={record} />
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
