import React, { Dispatch, memo, useState } from "react";
import { Button, Modal, Form, Input, message, Switch, Divider } from "antd";


type FormValues = {
  broker: string;
  port: string;
  username?: string;
  password?: string;
  report_image: boolean;
  report_url: string;
};

const _reportServerConfigCard = ({
  isVisible,
  baseUrl,
  defaultServerConifg,
  setServerConfig,
}: {
  isVisible: boolean;
  baseUrl: string;
  defaultServerConifg: FormValues;
  setServerConfig: Dispatch<any>;
}) => {
  const [visible, setVisible] = useState(isVisible);
  const [form] = Form.useForm<FormValues>();

  const showModal = () => {
    setVisible(true);
  };

  const handleSubmit = () => {
    form.validateFields().then((values: FormValues) => {
      fetch(`${baseUrl}/api/aibox_report/config/report`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(values),
      })
        .then((response) => response.json())
        .then((data) => {
          setServerConfig(values);
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
        title="上报地址切换"
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
            label="Mqtt地址"
            initialValue={defaultServerConifg.broker}
            rules={[{ required: true, message: "请输入对应的mqtt地址" }]}
          >
            <Input defaultValue={defaultServerConifg.broker} />
          </Form.Item>
          <Form.Item
            name="port"
            label="Mqtt端口"
            initialValue={defaultServerConifg.port}
            rules={[{ required: true, message: "请输入对应的mqtt端口" }]}
          >
            <Input defaultValue={defaultServerConifg.port} />
          </Form.Item>
          <Form.Item
            name="username"
            label="Mqtt账号"
            initialValue={defaultServerConifg.username}
            rules={[{ required: false }]}
          >
            <Input defaultValue={defaultServerConifg.username} />
          </Form.Item>
          <Form.Item
            name="password"
            label="Mqtt密码"
            initialValue={defaultServerConifg.password}
            rules={[{ required: false }]}
          >
            <Input.Password defaultValue={defaultServerConifg.password} />
          </Form.Item>
          <Divider />
          <Form.Item
            name="report_image"
            label="图片上报开关"
            initialValue={defaultServerConifg.report_image}
            rules={[{ required: true }]}
          >
            <Switch defaultValue={defaultServerConifg.report_image} />
          </Form.Item>
          <Form.Item
            name="report_url"
            label="图片上报地址"
            initialValue={defaultServerConifg.report_url}
            rules={[{ required: true }, { type: "url", message: "请输入正确的域名, http开头" }]}
          >
            <Input defaultValue={defaultServerConifg.report_url} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export const ServerConfigCard = memo(_reportServerConfigCard);
