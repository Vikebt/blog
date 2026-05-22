---
title: "Hello World — 我的第一篇博客"
date: 2026-05-22
tags: ["随笔", "博客"]
description: "欢迎来到我的学习笔记博客，这是第一篇文章。"
---

## 终于开始了

这是我的第一篇博客文章，从这里开始记录我的学习之旅。

## 关于这个博客

这个博客是用 **静态站点生成器** 搭建的，基于 Python + Markdown + Jinja2。你看到的每一页，都是从 Markdown 文件自动生成的。

### 特点

- 用 Markdown 写文章，放在 `content/posts/` 目录下
- 支持标签分类
- 支持全文搜索（按 `Ctrl + K` 或点击搜索按钮）
- 支持 RSS 订阅
- 支持夜间模式
- 响应式设计，手机也能看

## 如何写新文章

在 `content/posts/` 目录下新建一个 `.md` 文件，文件头写上元信息：

```yaml
---
title: "文章标题"
date: 2026-05-22
tags: ["标签1", "标签2"]
description: "文章简介"
---
```

然后写正文即可。写完运行 `python build.py` 就能生成更新后的网站。

## 代码示例

这是一段 Python 代码：

```python
def greet(name):
    print(f"Hello, {name}!")

greet("World")
```

这是一段 JavaScript：

```javascript
console.log("Hello from the browser!");
```

---

好了，开始记录吧！🚀
