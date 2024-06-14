import React, { memo, useState } from "react";
import { Button, Modal, Form, Input, message } from "antd";


type FormValues = {
  name: string;
  url: string;
};

const _addCamera = ( { baseUrl }: { baseUrl: string }) => {

  const [visible, setVisible] = useState(false);
  const [form] = Form.useForm<FormValues>();

  const showModal = () => {
    setVisible(true);
  };

  const handleCancel = () => {
    setVisible(false);
  };

  const handleSubmit = () => {
    form
      .validateFields()
      .then((values: FormValues) => {
        console.log("Received values of form:", values);
        const url = `${baseUrl}/api/aibox_camera/cameras/add`;
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
            message.success("添加成功");
            console.log("Success:", data);
          })
          .catch((error) => {
            message.error("添加失败: " + error);
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