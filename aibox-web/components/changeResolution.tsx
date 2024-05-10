import React, { memo, useState } from "react";
import { Button, Modal, Form, Select, message } from "antd";


const { Option } = Select;

export type LevelKeys = "origin" | "midele" | "low"

type props = {
  baseUrl: string;
  defaultLevel: LevelKeys;
};

type FormValues = {
  level: string;
};


const _changeResolution = ({ baseUrl, defaultLevel }: props) => {

  const [visible, setVisible] = useState(false);
  const [form] = Form.useForm<FormValues>();

  const showModal = () => {
    setVisible(true);
  };


  const LEVELS_CN: { [key: string]: string } = {
    "原视频": "origin",
    "标清(480P)": "middle",
    "流畅(360P)": "low",
  }

  const reversedLevels: { [key: string]: string } = {};

  Object.entries(LEVELS_CN).forEach(([key, value]) => {
    reversedLevels[value] = key;
  });


  const handleSubmit = () => {
    form
      .validateFields()
      .then((values: FormValues) => {
        console.log("Received values of form:", values);
        const url = `${baseUrl}:8010/api/aibox_camera/cameras/resolution`;
        // 发送Form数据到后端
        fetch(url, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            level: values["level"],
          }),
        })
          .then((response) => {
            response.status === 200
              ? message.success("更新成功")
              : message.error("更新失败");
          })
          .catch((error) => {
            message.error("更新失败");
            console.log("error:", error);
          })
          .finally(() => {
            setVisible(false); // 关闭对话框
          });
      })
      .catch((info: any) => {
        console.log("Validate Failed:", info);
      });
  };

  const SelectOptions = Object.entries(LEVELS_CN).map(([key, value]) => {
    return (
      <Option key={key} value={value}>
        {key}
      </Option>
    );
  });

  const handleCancel = () => {
    setVisible(false);
  };

  return (
    <>
      <Button type="primary" danger onClick={showModal}>
        修改分辨率
      </Button>
      <Modal
        title="修改分辨率"
        open={visible}
        onOk={handleSubmit}
        onCancel={handleCancel}
        okText="更新"
        cancelText="取消"
      >
        <Form form={form} layout="vertical" name="form_in_modal">
          <Form.Item
            name="level"
            label="分辨率"
            initialValue={reversedLevels[defaultLevel]}
            rules={[{ required: true, message: "请选择分辨率 !" }]}
          >
            <Select placeholder="请选择对应的分辨率">
                {SelectOptions}
            </Select>
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
};

export const ChangeResolution = memo(_changeResolution);
