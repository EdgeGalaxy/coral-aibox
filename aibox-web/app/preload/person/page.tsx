'use client'

import { useEffect, useState } from "react";
import type { GetProp, UploadFile, UploadProps } from 'antd';
import { Switch, Upload, message, Modal, Popconfirm, Button, Image } from 'antd';

import { getInternalHost } from '@/components/api/utils'
import { DeleteOutlined } from "@ant-design/icons";

type FileType = Parameters<GetProp<UploadProps, 'beforeUpload'>>[0];


export default function LoadPersonPage() {
  const [ baseUrl, setBaseUrl ] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [personRecord, setPersonRecord] = useState(false);
  const [personFileList, setPersonFileList] = useState<UploadFile<any>[]>([]);

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
    const personImagesUrl = `${baseUrl}:8020/api/aibox_person/fake/persons`;
    // person fetch
    fetch(personConfigUrl)
      .then((response) => response.json())
      .then((data) => {
        setPersonRecord(data['is_record'])
      })

    // person images
    fetch(personImagesUrl)
      .then((response) => response.json())
      .then((persons) => {
        console.log('personImagesUrl', persons)
        const fakePersonFileList: UploadFile<any>[] = []
        for (const person of persons) {
          console.log('person', person)
          const personImageUrl = `${baseUrl}:8020/static/${person}`
          const personFile: UploadFile = {
            // person形如： xxxx.jpg, uid 需要 xxxx
            uid: person.split('.')[0],
            // person形如： db/face/xxxx.jpg, name 需要 xxx.jpg
            name: person,
            status: 'done',
            url: personImageUrl,
          }
          console.log('personFile', personFile)
          fakePersonFileList.push(personFile)
        }
        setPersonFileList(fakePersonFileList)
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

  const handleRemove = (file: UploadFile<any>) => {
    const deleteFakePersonUrl = `${baseUrl}:8020/api/aibox_person/fake/persons/${file.uid}`
    fetch(deleteFakePersonUrl, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
      }
    })
        .then((response) => {
            if (response.ok) {
                console.log('删除成功')
                message.success('删除成功')
                const index = personFileList.indexOf(file);
                const newFileList = personFileList.slice();
                newFileList.splice(index, 1);
                setPersonFileList(newFileList);
            } else {
                message.error('删除失败')
            }
        })
  }

  // 自定义渲染上传列表项
  const onRemove = (file: UploadFile<any>) => (
    <Popconfirm
      title="确定要删除这个文件吗？"
      onConfirm={() => handleRemove(file)}
      okText="是"
      cancelText="否"
    >
      <Button size="small" className="text-red-500" icon={<DeleteOutlined />}>删除</Button>
    </Popconfirm>
  );


  return (
    <div>
        <div className="flex m-8">
          <p className="mr-4">误检人物数据录入</p>
          <Switch checkedChildren="开启" unCheckedChildren="关闭" loading={isLoading} defaultChecked={personRecord} checked={personRecord} onChange={() => onPersonSwitchChange(!personRecord)}/>
        </div>
        <div className="grid grid-cols-4 m-8">
            {personFileList.map((file) => (
                <div className="w-48 h-48 relative" key={file.uid}>
                <Image src={file.url} className="w-full h-full object-cover" alt="图片" />
                {onRemove(file)}
                </div>
            ))}
            </div>
    </div>
  );
}
