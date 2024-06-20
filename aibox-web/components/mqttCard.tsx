import React, { Dispatch, memo, useState } from "react";
import { Button, Modal, Form, Input, message } from "antd";

type FormValues = {
  broker: string;
  port: string;
  username?: string;
  password?: string;
};

const _mqttConfigCard = ({
  isVisible,
  baseUrl,
  defaultMqttConifg,
  setMqttConfig,
}: {
  isVisible: boolean;
  baseUrl: string;
  defaultMqttConifg: FormValues;
  setMqttConfig: Dispatch<any>;
}) => {
  const [visible, setVisible] = useState(isVisible);
  const [form] = Form.useForm<FormValues>();

  const showModal = () => {
    setVisible(true);
  };

  const handleSubmit = () => {
    form.validateFields().then((values: FormValues) => {
      fetch(`${baseUrl}/api/aibox_report/config/mqtt`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(values),
      })
        .then((response) => response.json())
        .then((data) => {
          setMqttConfig(values);
          setVisible(false);
          message.success("配置成功");
        })
        .catch((error: any) => {
          message.error("配置失败, 确认是否地址正确");
        });
    });
  };

  const handleCancel = () => {
    setVisible(false);
  };

  return (
    <div>
      <Button type="primary" onClick={showModal}>
        更新上报地址
      </Button>
      <Modal
        title="Mqtt切换"
        keyboard={false}
        open={visible}
        onOk={handleSubmit}
        onCancel={handleCancel}
        okText="切换"
        cancelText="取消"
      >
        <Form form={form} layout="vertical" name="form_in_modal">
          <Form.Item
            name="broker"
            label="地址"
            initialValue={defaultMqttConifg.broker}
            rules={[{ required: true, message: "请输入对应的mqtt地址" }]}
          >
            <Input defaultValue={defaultMqttConifg.broker} />
          </Form.Item>
          <Form.Item
            name="port"
            label="端口"
            initialValue={defaultMqttConifg.port}
            rules={[{ required: true, message: "请输入对应的mqtt端口" }]}
          >
            <Input defaultValue={defaultMqttConifg.port} />
          </Form.Item>
          <Form.Item
            name="username"
            label="账号"
            initialValue={defaultMqttConifg.username}
            rules={[{ required: false }]}
          >
            <Input defaultValue={defaultMqttConifg.username} />
          </Form.Item>
          <Form.Item
            name="password"
            label="密码"
            initialValue={defaultMqttConifg.password}
            rules={[{ required: false }]}
          >
            <Input.Password defaultValue={defaultMqttConifg.password} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export const MqttConfigCard = memo(_mqttConfigCard);
