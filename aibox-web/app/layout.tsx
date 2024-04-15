"use client";

import "./globals.css";
import { Inter } from "next/font/google";
import Link from "next/link";

import {
  DesktopOutlined,
  RedoOutlined,
  HomeOutlined,
  SunOutlined,
} from "@ant-design/icons";
import { Layout, Menu, theme } from "antd";
import { useState } from "react";

const { Header, Content, Footer, Sider } = Layout;

const inter = Inter({ subsets: ["latin"] });

const menuItems = [
  {
    label: "显示",
    key: "1",
    url: "/",
    icon: <HomeOutlined />,
  },
  {
    label: "配置",
    key: "2",
    url: "/configuration",
    icon: <DesktopOutlined />,
  },
  {
    label: "预热",
    key: "3",
    url: "/preload",
    icon: <RedoOutlined />,
  },
  {
    label: "测试",
    key: "4",
    url: "/predict",
    icon: <SunOutlined />,
  },
];

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const [collapsed, setCollapsed] = useState(false);
  const {
    token: { colorBgContainer },
  } = theme.useToken();

  return (
    <html lang="en">
      <body className={inter.className}>
        <Layout style={{ minHeight: "100vh" }}>
          <Sider
            collapsible
            collapsed={collapsed}
            onCollapse={(value) => setCollapsed(value)}
          >
            <div className="demo-logo-vertical" />
            <Menu
              theme="dark"
              defaultSelectedKeys={["1"]}
              mode="inline"
              items={menuItems.map((item) => {
                return {
                  key: item.key,
                  icon: item.icon,
                  label: <Link href={item.url}>{item.label}</Link>,
                };
              })}
            />
          </Sider>
          <Layout>
            <Header style={{ padding: 0, background: colorBgContainer }} />
            <Content style={{ margin: "0 16px" }}>{children}</Content>
            <Footer style={{ textAlign: "center" }}>
              LoopTech ©{new Date().getFullYear()} Created by LoopTech
            </Footer>
          </Layout>
        </Layout>
      </body>
    </html>
  );
}
