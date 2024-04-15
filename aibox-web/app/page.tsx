'use client'

import { useState, useEffect } from "react";
import { Image } from "antd";

export default function Home() {
  const [cameras, SetCameras] = useState([]);

  useEffect(() => {
    fetch(`http://localhost:8010/api/aibox_camera/cameras`)
      .then((response) => response.json())
      .then((cameras) => SetCameras(cameras));
  }, []);

  return (
    <div className="grid grid-cols-2 gap-4">
      {cameras.map((camera_id: string) => {
        const videoUrl = `http://localhost:8010/api/aibox_camera/cameras/${camera_id}/stream`;
        return (
          <div>
            <Image key={camera_id} className="w-full" alt={camera_id} src={videoUrl} />
            <p className="text-center font-blod">{camera_id}</p>
          </div>
        );
      })}
    </div>
  );
}
