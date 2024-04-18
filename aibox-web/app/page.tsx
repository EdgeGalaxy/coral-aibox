'use client'

import { useState, useEffect } from "react";
import { Button, Image } from "antd";

export default function Home() {
  const BASE_URL = process.env.NEXT_PUBLIC_AIBOX_HOST || 'http://localhost'
  const [cameras, SetCameras] = useState([]);

  useEffect(() => {
    fetch(`${BASE_URL}:8010/api/aibox_camera/cameras`)
      .then((response) => response.json())
      .then((cameras) => SetCameras(cameras));
  }, []);

  return (
    <div className="grid grid-cols-2 gap-4">
      <Button onClick={() => window.location.reload()}>新增Camera</Button>
      {cameras.map((camera_id: string) => {
        const videoUrl = `${BASE_URL}:8010/api/aibox_camera/cameras/${camera_id}/stream`;
        return (
          <div>
            <Image key={camera_id} className="w-full" alt={camera_id} src={videoUrl} />
            <Button key={camera_id} onClick={() => window.location.reload()}>删除Camera</Button>
            <p className="text-center font-blod">{camera_id}</p>
          </div>
        );
      })}
    </div>
  );
}
