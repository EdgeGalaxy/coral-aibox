
import { Button, Spin } from "antd";
import { memo, useEffect, useState } from "react";

import { Mask } from "./canvas";

import { getInternalHost } from "./api/utils";


type CameraConfig = {
  iou_scale: number
  points: number[][]
}


const _CameraMask = ({ camera_id} : { camera_id: string }) => {
  const BASE_URL = getInternalHost()
  const url = `${BASE_URL}:8010/api/aibox_camera/cameras/${camera_id}/mask`
  const cameraConfigUrl = `${BASE_URL}:8010/api/aibox_camera/cameras/${camera_id}/config`
  const [coordinates, setCoordinates] = useState<{ x: number; y: number }[]>([]);
  const [snapshotUrl, setSnapshotUrl] = useState<string>("");
  const [cameraConfig, setCameraConfig] = useState<CameraConfig>({} as CameraConfig);

  useEffect(() => {
    fetch(cameraConfigUrl)
      .then((response) => {
        if (!response.ok) {
          throw new Error('Network response was not ok');
        }
        return response.json()
      })
      .then((config: CameraConfig) => {
        const points: number[][] = config['points']
        setCameraConfig(config)
        if (points.length === 0) {
            setSnapshotUrl(url)
          return
        }
        const pointsStr: string = points.flatMap(point => point).join(',')
        const maskUrl = url + `?points=${pointsStr}`
        setSnapshotUrl(maskUrl)
      });
  }, []);

  const updateCoordinate = (newCoordinates: { x: number; y: number }) => {
    setCoordinates(() => [...coordinates, newCoordinates]);
  };

  const handlePreviewClick = () => {
    const pointsStr = coordinates.map(point => `${point.x},${point.y}`).join(',')
    const maskUrl = url + `?points=${pointsStr}`
    setSnapshotUrl(maskUrl)
    console.log("预览Mask", snapshotUrl);
  };

  const handleClearClick = () => {
    setSnapshotUrl(url)
    setCoordinates([])
    console.log("清除Mask", snapshotUrl);
  };

  const handleSaveClick = () => {
    const points = coordinates.map(point => [point.x, point.y])
    const pointsStr = coordinates.map(point => `${point.x},${point.y}`).join(',')
    const maskUrl = url + `?points=${pointsStr}`
    setSnapshotUrl(maskUrl)
    setCameraConfig({ ...cameraConfig, points: points })

    // 保存到后端
    fetch(cameraConfigUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        'iou_scale': cameraConfig['iou_scale'],
        'points': points
      }),
    })
      .then((response) => response.json())
      .then((data) => {
        console.log('Success:', data);
      })
      .catch((error) => {
        console.error('Error:', error);
      });
    console.log("保存Mask", snapshotUrl);
  };

  if (snapshotUrl === "") {
    return <div>Loading...</div>;
  }

  return (
      <div className="flex">
          < div className="mb-2">
            <Mask url={snapshotUrl} updateCoordinate={updateCoordinate}/>
            <p className="font-mono text-center text-base font-blod">{camera_id}</p>
            </div>
        <div className="flex-col">
          <Button className="m-2" type="primary" onClick={handlePreviewClick}>预览Mask</Button>
          <Button className="m-2" type="primary" onClick={handleClearClick}>清除Mask</Button>
          <Button className="m-2" type="primary" onClick={handleSaveClick}>保存Mask</Button>
        </div>
      </div>
  );
}


export const CameraMask = memo(_CameraMask);