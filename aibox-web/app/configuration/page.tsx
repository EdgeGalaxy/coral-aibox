
'use client'

import { CameraMask } from "@/components/cameraMask";
import { useEffect, useState } from "react";
import { getInternalHost } from '@/components/api/utils'


type CameraConfig = {
  iou_scale: number
  points: number[][]
}


export default function Configuration() {

  const BASE_URL = getInternalHost()
  const [cameras, SetCameras] = useState([]);

  useEffect(() => {
    fetch(`${BASE_URL}:8010/api/aibox_camera/cameras`)
      .then((response) => response.json())
      .then((cameras) => SetCameras(cameras));
  }, []);


  return (
      <div className="grid grid-cols-2 gap-4">
        {cameras.map((camera_id: string) => {
          return <CameraMask key={camera_id} camera_id={camera_id} />
        })}
      </div>
  );
}
