import React, { memo, useState } from "react";
import { Button, Modal, Form, Input } from "antd";

import { getInternalHost } from "./api/utils";

type FormValues = {
  name: string;
  url: string;
};

const _addCamera = () => {
  const BASE_URL = getInternalHost();
  const url = `${BASE_URL}:8010/api/aibox_camera/cameras/add`;

  const [visible, setVisible] = useState(false);
  const [form] = Form.useForm<FormValues>();

  const showModal = () => {
    setVisible(true);
  };

  const handleSubmit = () => {
    form
      .validateFields()
      .then((values: FormValues) => {
        console.log("Received values of form:", values);
        // 发送Form数据到后端
        fetch(url, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            name: values["name"],
            url: values["url"],
          }),
        })
          .then((response) => response.json())
          .then((data) => {
            console.log("Success:", data);
          })
          .catch((error) => {
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

  const handleCancel = () => {
    setVisible(false);
  };

  return (
    <>
      <Button type="primary" onClick={showModal}>
        添加摄像头
      </Button>
      <Modal
        title="添加摄像头"
        open={visible}
        onOk={handleSubmit}
        onCancel={handleCancel}
        okText="添加并重启"
        cancelText="取消"
      >
        <Form form={form} layout="vertical" name="form_in_modal">
          <Form.Item
            name="name"
            label="摄像头ID"
            rules={[
              { required: true, message: "请输入摄像头ID, 英文唯一ID !" },
            ]}
          >
            <Input />
          </Form.Item>
          <Form.Item
            name="url"
            label="摄像头地址"
            rules={[{ required: true, message: "请输入摄像头URL !" }]}
          >
            <Input />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
};


export const AddCamera = memo(_addCamera);