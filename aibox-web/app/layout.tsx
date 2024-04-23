"use client";

import "./globals.css";
import { usePathname } from 'next/navigation';

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
    key: "/",
    url: "/",
    icon: <HomeOutlined />,
  },
  {
    label: "Mask配置",
    key: "/mask",
    url: "/mask",
    icon: <DesktopOutlined />,
  },
  {
    label: "预加载",
    key: "/preload",
    url: "/preload",
    icon: <RedoOutlined />,
    children: [
      {
        label: "人物误检",
        key: "/preload/person",
        url: "/preload/person",
        icon: <SunOutlined />,
      },
      {
        label: "面部识别",
        key: "/preload/face",
        url: "/preload/face",
        icon: <RedoOutlined />,
      }
    ]
  }
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

  // 获取当前路径
  const currentPath = usePathname()

  // 确定哪个菜单项应该高亮
  const selectedKeys = menuItems
    .filter(item => currentPath === item.key)
    .map(item => item.key);

  return (
    <html lang="en">
      <body className={inter.className}>
        <Layout style={{ minHeight: "100vh" }}>
          <Sider
            collapsible
            collapsed={collapsed}
            onCollapse={(value) => setCollapsed(value)}
          >
            <div className="demo-logo-vertical mb-12" />
            <Menu
              theme="dark"
              defaultSelectedKeys={selectedKeys}
              mode="inline"
              items={menuItems.map((item) => {
                return {
                  key: item.key,
                  icon: item.icon,
                  label: <Link href={item.url}>{item.label}</Link>,
                  children: item.children?.map(child => {
                    return {
                      key: child.key,
                      icon: child.icon,
                      label: <Link href={child.url}>{child.label}</Link>
                    }
                  })
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
