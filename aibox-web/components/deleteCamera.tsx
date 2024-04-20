import React, { memo, useState } from "react";
import { ExclamationCircleOutlined } from '@ant-design/icons';
import { Button, Modal, Form, Select, message } from "antd";

import { getInternalHost } from "./api/utils";

const { Option } = Select;

type props = {
  cameraIds: string[];
};

type FormValues = {
  name: string;
};

const _deleteCamera = ({ cameraIds }: props) => {
  const BASE_URL = getInternalHost();

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
        const url = `${BASE_URL}:8010/api/aibox_camera/cameras/${cameraIds}`;
        // 发送Form数据到后端
        fetch(url, {
          method: "DELETE",
          headers: {
            "Content-Type": "application/json",
          },
        })
          .then((response) => {
            response.status === 200
              ? message.success("删除成功")
              : message.error("删除失败");
          })
          .catch((error) => {
            message.error("删除失败");
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
      <Button type="primary" danger onClick={showModal}>
        删除摄像头
      </Button>
      <Modal
        title="删除摄像头"
        open={visible}
        onOk={handleSubmit}
        onCancel={handleCancel}
        okText="删除并重启"
        cancelText="取消"
      >
        <Form form={form} layout="vertical" name="form_in_modal">
          <Form.Item
            name="name"
            label="摄像头ID"
            rules={[{ required: true, message: "请选择一个摄像头ID !" }]}
          >
            <Select placeholder="请选择摄像头ID">
              {cameraIds.map((id) => (
                <Option key={id} value={id}>
                  {id}
                </Option>
              ))}
            </Select>
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
};

export const DeleteCamera = memo(_deleteCamera);
