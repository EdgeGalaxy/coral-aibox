"use client";

import { Dispatch, SetStateAction, useEffect, useState } from "react";
import type { InputNumberProps, UploadFile } from "antd";
import {
  Switch,
  message,
  Popconfirm,
  Button,
  Image,
  InputNumber,
  Slider,
  Row,
  Col,
} from "antd";

import { getInternalHost } from "@/components/api/utils";
import { DeleteOutlined } from "@ant-design/icons";
import { ImageCard } from "@/components/cardImage";


export default function LoadPersonPage() {
  const [baseUrl, setBaseUrl] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [switchs, setSwitchs] = useState<{ [key: string]: boolean | number }>({
    is_record: false,
    is_open: true,
    confidence_thresh: 0.5,
    sim_threshold: 0.9,
  });
  const [personFileList, setPersonFileList] = useState<UploadFile<any>[]>([]);
  const [confidenceThresh, setConfidenceThresh] = useState(0.5);
  const [similarThresh, setSimilarThresh] = useState(0.9);

  useEffect(() => {
    const fetchInternalIP = async () => {
      const internalHost = await getInternalHost();
      console.log("internalHost", internalHost);
      setBaseUrl(internalHost);
      return internalHost;
    };
    fetchInternalIP();
  }, []);

  useEffect(() => {
    const personConfigUrl = `${baseUrl}:8020/api/aibox_person/config`;
    const personImagesUrl = `${baseUrl}:8020/api/aibox_person/fake/persons`;
    // person fetch
    fetch(personConfigUrl)
      .then((response) => response.json())
      .then((data) => {
        setSwitchs({
          is_record: data["is_record"],
          is_open: data["is_open"],
          sim_threshold: data["featuredb"]["sim_threshold"],
          confidence_thresh: data["detection"]["confidence_thresh"],
        });
        setConfidenceThresh(data["detection"]["confidence_thresh"]);
        setSimilarThresh(data["featuredb"]["sim_threshold"]);
      });

    // person images
    fetch(personImagesUrl)
      .then((response) => response.json())
      .then((persons) => {
        const fakePersonFileList: UploadFile<any>[] = [];
        for (const person of persons) {
          const personImageUrl = `${baseUrl}:8020/static/${person}`;
          const personFile: UploadFile = {
            // person形如： xxxx.jpg, uid 需要 xxxx
            uid: person.split(".")[0],
            // person形如： db/face/xxxx.jpg, name 需要 xxx.jpg
            name: person,
            status: "done",
            url: personImageUrl,
          };
          fakePersonFileList.push(personFile);
        }
        setPersonFileList(fakePersonFileList);
      });
  }, [baseUrl]);

  useEffect(() => {
    console.log("switchs", switchs);
  }, [switchs]);

  const onPersonSwitchChange = (key: string, checked: boolean | number) => {
    setIsLoading(true);
    const personRecordUrl = `${baseUrl}:8020/api/aibox_person/record/featuredb`;
    let { [key]: _, ...otheSwitchs } = switchs;
    fetch(personRecordUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        [key]: checked,
        ...otheSwitchs,
      }),
    })
      .then(() => {
        setSwitchs({ ...switchs, [key]: checked });
        console.log("onPersonSwitchChange", key, checked, "更新成功");
      })
      .catch((error: any) => {
        console.error("onPersonSwitchChange", key, checked, "Error:", error);
      })
      .finally(() => {
        setIsLoading(false);
      });
  };

  const handleRemove = (file: UploadFile<any>) => {
    const deleteFakePersonUrl = `${baseUrl}:8020/api/aibox_person/fake/persons/${file.uid}`;
    fetch(deleteFakePersonUrl, {
      method: "DELETE",
      headers: {
        "Content-Type": "application/json",
      },
    }).then((response) => {
      if (response.ok) {
        console.log("删除成功");
        message.success("删除成功");
        const index = personFileList.indexOf(file);
        const newFileList = personFileList.slice();
        newFileList.splice(index, 1);
        setPersonFileList(newFileList);
      } else {
        message.error("删除失败");
      }
    });
  };

  // 自定义渲染上传列表项
  const onRemove = (file: UploadFile<any>) => (
    <Popconfirm
      title="确定要删除这个文件吗？"
      onConfirm={() => handleRemove(file)}
      okText="是"
      cancelText="否"
    >
      <Button size="small" className="text-red-500" icon={<DeleteOutlined />}>
        删除
      </Button>
    </Popconfirm>
  );

  const onSliderChange = (key: string, newValue: number, setFunc: Dispatch<SetStateAction<number>>) => {
    setFunc(newValue);
    onPersonSwitchChange(key, newValue);
  };

  return (
    <div>
      <div className="flex">
        <div className="flex m-8">
          <p className="mr-4">误检人物数据录入</p>
          <Switch
            checkedChildren="开启"
            unCheckedChildren="关闭"
            loading={isLoading}
            defaultChecked={switchs.is_record as boolean}
            checked={switchs.is_record as boolean}
            onChange={() =>
              onPersonSwitchChange("is_record", !switchs.is_record)
            }
          />
        </div>
        <div className="flex m-8">
          <p className="mr-4">人物检测开关</p>
          <Switch
            checkedChildren="开启"
            unCheckedChildren="关闭"
            disabled
            loading={isLoading}
            defaultChecked={switchs.is_open as boolean}
            checked={switchs.is_open as boolean}
            onChange={() => onPersonSwitchChange("is_open", !switchs.is_open)}
          />
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
      </div>
        <div style={{ display: 'flex', flexWrap: 'wrap' }}>
        {personFileList.map((file, index) => (
            <ImageCard key={index} imageUrl={file.url as string} handleDelete={() => handleRemove(file)} />
        ))}
      </div>
    </div>
  );
}
