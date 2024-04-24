'use client'

import { useEffect, useState } from "react";
import { Switch, Button, message } from 'antd';

import { getInternalHost } from '@/components/api/utils'
import { UsersFaceFolderList } from '@/components/usersFaceList'
import { ItemData } from "@/components/types/type";



export default function PreloadFacePage() {

  const [ baseUrl, setBaseUrl ] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [ switchs, setSwitchs] = useState<{ [key: string]: boolean}>({is_record: false, is_open: true});
  const [ users, setUsers ] = useState<ItemData[]>([]);

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
        setSwitchs({is_record: data['is_record'], is_open: data['is_open']})
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

  const onFaceRecordSwitchChange = (key: string, checked: boolean) => {
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

  return (
    <div>
        <div className="flex">
            <div className="flex m-8">
            <p className="mr-4">人物面部识别录入</p>
            <Switch checkedChildren="开启" unCheckedChildren="关闭" loading={isLoading} defaultChecked={switchs.is_record} checked={switchs.is_record} onChange={() => onFaceRecordSwitchChange('is_record', !switchs.is_record)}/>
            </div>
            <div className="flex m-8">
            <p className="mr-4">面部检测开关</p>
            <Switch checkedChildren="开启" unCheckedChildren="关闭" loading={isLoading} defaultChecked={switchs.is_open} checked={switchs.is_open} onChange={() => onFaceRecordSwitchChange('is_open', !switchs.is_open)}/>
            </div>
            <Button className="ml-20 mt-6" type="primary" onClick={onSyncButtonClick}>广播面部信息</Button>
        </div>
        <div>
            <UsersFaceFolderList baseUrl={baseUrl} data={users} />
        </div>
    </div>
  );
}
