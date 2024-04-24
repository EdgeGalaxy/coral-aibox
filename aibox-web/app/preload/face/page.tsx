'use client'

import { Dispatch, SetStateAction, useEffect, useState } from "react";
import { Switch, Button, message, Row, Col, Slider, InputNumber } from 'antd';

import { getInternalHost } from '@/components/api/utils'
import { UsersFaceFolderList } from '@/components/usersFaceList'
import { ItemData } from "@/components/types/type";



export default function PreloadFacePage() {

  const [ baseUrl, setBaseUrl ] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [switchs, setSwitchs] = useState<{ [key: string]: boolean | number }>({
    is_record: false,
    is_open: true,
    confidence_thresh: 0.5,
    sim_threshold: 0.9,
  });  
  const [ users, setUsers ] = useState<ItemData[]>([]);
  const [confidenceThresh, setConfidenceThresh] = useState(0.5);
  const [similarThresh, setSimilarThresh] = useState(0.9);

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
    const faceConfigUrl = `${baseUrl}:8030/api/aibox_face/config`;
    const usersFaceUrl = `${baseUrl}:8030/api/aibox_face/users`;
    // face fetch
    fetch(faceConfigUrl)
      .then((response) => response.json())
      .then((data) => {
        console.log('faceConfigUrl', data)
        setSwitchs({          is_record: data["is_record"],
        is_open: data["is_open"],
        sim_threshold: data["featuredb"]["sim_threshold"],
        confidence_thresh: data["detection"]["confidence_thresh"],})
      })
    // users fetch
    fetch(usersFaceUrl)
      .then((response) => response.json())
      .then((_users) => {
        Object.keys(_users).forEach((key) => {
            const faces = _users[key];
            const facesData: ItemData[] = []
            for (const idx in faces) {
                const faceData: ItemData = {
                    id: faces[idx],
                    name: faces[idx],
                    type: 'file',
                }
                facesData.push(faceData)
            }
            const userData: ItemData = {
                id: key,
                name: key,
                type: 'folder',
                children: facesData

            };
            setUsers(users => [...users, userData]);
        })
        console.log('users', _users)
      })

  }, [baseUrl]);

  const onFaceRecordSwitchChange = (key: string, checked: boolean | number) => {
    setIsLoading(true)
    const faceRecordUrl = `${baseUrl}:8030/api/aibox_face/record/featuredb`;
    let { [key]: _, ...otheSwitchs } = switchs
    fetch(faceRecordUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        [key]: checked,
        ...otheSwitchs
      }),
    }).then(() => {
      setSwitchs({...switchs, [key]: checked})
      console.log('onFaceSwitchChange', key, checked, '更新成功')
    }).catch((error: any) => {
      console.error('onFaceSwitchChange', key, checked, 'Error:', error);
    }).finally(() => {
      setIsLoading(false)
    })
  };

  const onSyncButtonClick = () => {
    console.log('onSyncButtonClick')
    fetch(`${baseUrl}:8030/api/aibox_face/users/sync`)
      .then((response) => {
        if (response.ok) {
            message.success('同步成功')
      } else {
          message.error('同步失败')
      }}).catch((error) => {
          message.error('同步失败')
      })
  }

  const onSliderChange = (key: string, newValue: number, setFunc: Dispatch<SetStateAction<number>>) => {
    setFunc(newValue);
    onFaceRecordSwitchChange(key, newValue);
  };

  return (
    <div>
        <div className="flex">
            <div className="flex m-8">
            <p className="mr-4">人物面部识别录入</p>
            <Switch checkedChildren="开启" unCheckedChildren="关闭" loading={isLoading} defaultChecked={switchs.is_record as boolean} checked={switchs.is_record as boolean} onChange={() => onFaceRecordSwitchChange('is_record', !switchs.is_record)}/>
            </div>
            <div className="flex m-8">
            <p className="mr-4">面部检测开关</p>
            <Switch checkedChildren="开启" unCheckedChildren="关闭" loading={isLoading} defaultChecked={switchs.is_open as boolean} checked={switchs.is_open as boolean} onChange={() => onFaceRecordSwitchChange('is_open', !switchs.is_open)}/>
            </div>
            <div className="flex m-8">
          <p className="mr-4">检测阈值</p>
          <Row>
            <Col span={12}>
              <Slider
                min={0}
                max={1}
                onChange={(value) => onSliderChange("confidence_thresh", value, setConfidenceThresh)}
                value={typeof confidenceThresh === "number" ? confidenceThresh : 0}
                step={0.05}
              />
            </Col>
            <Col span={4}>
              <InputNumber
                min={0}
                max={1}
                style={{ margin: "0 16px" }}
                step={0.05}
                value={confidenceThresh}
                onChange={(value) =>
                  onSliderChange("confidence_thresh", value as number, setConfidenceThresh)
                }
              />
            </Col>
          </Row>
        </div>
        <div className="flex m-8">
          <p className="mr-4">相似度阈值</p>
          <Row>
            <Col span={12}>
              <Slider
                min={0}
                max={1}
                onChange={(value) => onSliderChange("sim_threshold", value, setSimilarThresh)}
                value={typeof similarThresh === "number" ? similarThresh : 0}
                step={0.05}
              />
            </Col>
            <Col span={4}>
              <InputNumber
                min={0}
                max={1}
                style={{ margin: "0 16px" }}
                step={0.05}
                value={similarThresh}
                onChange={(value) =>
                  onSliderChange("sim_threshold", value as number, setSimilarThresh)
                }
              />
            </Col>
          </Row>
        </div>
            <Button className="ml-20 mt-6" type="primary" onClick={onSyncButtonClick}>广播面部信息</Button>
        </div>
        <div>
            <UsersFaceFolderList baseUrl={baseUrl} data={users} />
        </div>
    </div>
  );
}
