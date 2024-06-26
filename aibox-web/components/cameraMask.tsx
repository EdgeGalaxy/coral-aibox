
import { Button, message } from "antd";
import { memo, useEffect, useState } from "react";

import { Mask } from "./canvas";


type CameraConfig = {
  iou_scale: number
  points: number[][]
}


const _CameraMask = ({ camera_id, baseUrl } : { camera_id: string, baseUrl: string }) => {
  const [ BaseMaskUrl, setUrl ] = useState("");
  const [ cameraConfigUrl, setCameraConfigUrl] = useState("");
  const [ coordinates, setCoordinates] = useState<{ x: number; y: number }[]>([]);
  const [ snapshotUrl, setSnapshotUrl] = useState<string>("");
  const [ cameraConfig, setCameraConfig] = useState<CameraConfig>({} as CameraConfig);

  useEffect(() => {
    setUrl(`${baseUrl}/api/aibox_camera/cameras/${camera_id}/draw-mask`)
    setCameraConfigUrl(`${baseUrl}/api/aibox_camera/cameras/${camera_id}/config`)
    setCoordinates([])
  }, [camera_id]);

  useEffect(() => {
    if (cameraConfigUrl === "") {
      console.log('empty cameraConfigUrl', cameraConfigUrl)
      return
    }
    if (BaseMaskUrl === "") {
      console.log('empty BaseMaskUrl', BaseMaskUrl)
      return
    }

    fetch(cameraConfigUrl)
      .then((response) => {
        if (!response.ok) {
          throw new Error('Network response was not ok');
        }
        return response.json()
      })
      .then((config: CameraConfig) => {
        const points: number[][] = config['points']
        console.log('points', points)
        setCameraConfig(config)
        if (points.length === 0) {
            setSnapshotUrl(BaseMaskUrl)
          return
        }
        const pointsStr: string = points.flatMap(point => point).join(',')
        const maskUrl = BaseMaskUrl + `?points=${pointsStr}`
        setSnapshotUrl(maskUrl)
        setCoordinates(points.map(point => ({ x: point[0], y: point[1] })))
      });
  }, [BaseMaskUrl, cameraConfigUrl]);

  // 为了首次加载出图片
  useEffect(() => {
    if (snapshotUrl === "") {
      return
    }
    const pointsStr = coordinates.map(point => `${point.x},${point.y}`).join(',')
    const maskUrl = BaseMaskUrl + `?points=${pointsStr}`
    console.log('maskurl', maskUrl)
    setSnapshotUrl(maskUrl)
    // handlePreviewClick()
  }, [snapshotUrl]);

  const updateCoordinate = (newCoordinates: { x: number; y: number }) => {
    setCoordinates(() => [...coordinates, newCoordinates]);
  };

  const handlePreviewClick = () => {
    const pointsStr = coordinates.map(point => `${point.x},${point.y}`).join(',')
    const maskUrl = BaseMaskUrl + `?points=${pointsStr}`
    setSnapshotUrl(maskUrl)
  };

  const handleClearClick = () => {
    setSnapshotUrl(BaseMaskUrl)
    setCoordinates([])
  };

  const handleSaveClick = () => {
    const points = coordinates.map(point => [point.x, point.y])
    const pointsStr = coordinates.map(point => `${point.x},${point.y}`).join(',')
    const maskUrl = BaseMaskUrl + `?points=${pointsStr}`
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
        message.success('保存成功');
      })
      .catch((error) => {
        console.error('保存失败', error);
        message.error('保存失败')
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
        <div className="flex flex-col">
          <Button className="m-2" type="primary" onClick={handlePreviewClick}>预览Mask</Button>
          <Button className="m-2" type="primary" onClick={handleClearClick}>清除Mask</Button>
          <Button className="m-2" type="primary" onClick={handleSaveClick}>保存Mask</Button>
        </div>
      </div>
  );
}


export const CameraMask = memo(_CameraMask);