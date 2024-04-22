'use client'

import { useEffect, useState } from "react";
import { Switch } from 'antd';

import { getInternalHost } from '@/components/api/utils'

export default function Home() {

  const [ baseUrl, setBaseUrl ] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [personRecord, setPersonRecord] = useState(false);
  const [faceRecord, setFaceRecord] = useState(false);

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
    const personConfigUrl = `${baseUrl}:8020/api/aibox_person/config`;
    const faceConfigUrl = `${baseUrl}:8030/api/aibox_face/config`;
    // person fetch
    fetch(personConfigUrl)
      .then((response) => response.json())
      .then((data) => {
        console.log('personConfigUrl', data)
        setPersonRecord(data['is_record'])
      })

    // face fetch
    fetch(faceConfigUrl)
      .then((response) => response.json())
      .then((data) => {
        console.log('faceConfigUrl', data)
        setFaceRecord(data['is_record'])
      })

  }, [baseUrl]);

  const onPersonSwitchChange = (checked: boolean) => {
    setIsLoading(true)
    const personRecordUrl = `${baseUrl}:8020/api/aibox_person/record/featuredb`;
    fetch(personRecordUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        'is_record': checked
      }),
    }).then(() => {
      setPersonRecord(checked)
      console.log('onPersonSwitchChange', checked, '更新成功')
    }).catch((error: any) => {
      console.error('onPersonSwitchChange', checked, 'Error:', error);
    }).finally(() => {
      setIsLoading(false)
    })
  };

  const onFaceSwitchChange = (checked: boolean) => {
    setIsLoading(true)
    const faceRecordUrl = `${baseUrl}:8030/api/aibox_face/record/featuredb`;
    fetch(faceRecordUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        'is_record': checked
      }),
    }).then(() => {
      setFaceRecord(checked)
      console.log('onFaceSwitchChange', checked, '更新成功')
    }).catch((error: any) => {
      console.error('onFaceSwitchChange', checked, 'Error:', error);
    }).finally(() => {
      setIsLoading(false)
    })
  };

  return (
    <div className="flex">
        <div className="flex m-8">
          <p className="mr-4">误检人物数据录入</p>
          <Switch checkedChildren="开启" unCheckedChildren="关闭" loading={isLoading} defaultChecked={personRecord} checked={personRecord} onChange={() => onPersonSwitchChange(!personRecord)}/>
        </div>
        <div className="flex m-8">
          <p className="mr-4">人物面部识别录入</p>
          <Switch checkedChildren="开启" unCheckedChildren="关闭" loading={isLoading} defaultChecked={faceRecord} checked={faceRecord} onChange={() => onFaceSwitchChange(!faceRecord)}/>
        </div>
    </div>
  );
}
