# 第 3 章 深入探究文件 I/O — 复习笔记

> **教材**：《I.MX6U 嵌入式 Linux C 应用编程指南》（正点原子）  
> **配图**：`images/figures/corrected/fig-3-x-x-x.png`（`fig-3-2-1.png` = 图 3.2.1）

---

## 本章目录

3.1 Linux 如何管理文件 · 3.2 errno · 3.3 退出 · 3.4 空洞文件 · 3.5 O_TRUNC/O_APPEND  
3.6 多次 open · 3.7 dup/dup2 · 3.8 文件共享 · 3.9 原子与竞态 · 3.10 fcntl/ioctl · 3.11 截断

---

## 3.1 Linux 系统如何管理文件

### 3.1.1 静态文件、inode、块

| 概念 | 说明 |
|------|------|
| 静态文件 | 未打开时存放在磁盘块设备上 |
| 扇区 Sector | 常 512B，磁盘最小存储单位 |
| 块 Block | 常 4KB（8 扇区），文件 I/O 常用单位 |
| inode 区 | 格式化后存放 inode table |
| 数据区 | 存放文件真实内容 |

**inode 记录**：大小、所有者、权限、时间戳、类型、数据 block 位置等。**文件名不在 inode 中**（目录项维护「名 → inode 号」）。

![图 3.1.1](images/figures/corrected/fig-3-1-1.png)

| 命令 | 作用 |
|------|------|
| `ls -i` | 查看 inode 编号（图 3.1.2） |
| `stat` | 查看 inode 详情（图 3.1.3） |

![图 3.1.2](images/figures/corrected/fig-3-1-2.png) ![图 3.1.3](images/figures/corrected/fig-3-1-3.png)

**快速格式化**：只删 inode 表，数据区仍在 → 数据可恢复（图 3.1.4）。

![图 3.1.4](images/figures/corrected/fig-3-1-4.png)

**路径打开文件三步**：① 文件名 → inode 号 → ② 查 inode table → ③ 按 block 指针读数据。

### 3.1.2 动态文件

`open` 后内核在内存维护**动态文件**（内核缓冲），读写主要对内存操作，再由内核异步写回磁盘。

| 现象 | 原因 |
|------|------|
| 开大文件慢 | 载入内核缓冲 |
| 未保存断电丢数据 | 改动可能仅在内存 |
| 用内存做缓存 | 块设备按块改写慢；内存随机访问快 |

### 3.1.3 PCB、fd 表、文件表、inode

![图 3.1.5](images/figures/corrected/fig-3-1-5.png)

- **fd**：进程内索引，非文件本体  
- **文件表**：每 fd 一条，含标志、**引用计数**、**当前偏移**、inode 指针  
- **inode**：标识磁盘上同一文件

---

## 3.2 返回错误处理与 errno

- 失败常返回 `-1`，原因在 **`errno`**（`#include <errno.h>`，每进程一份，**后错覆盖前错**）。
- 是否设置 errno：查 **`man 2 函数名`** 的 RETURN VALUE。

![图 3.2.1](images/figures/corrected/fig-3-2-1.png)

### strerror 与 perror 对比

| 对比项 | `strerror(errno)` | `perror("前缀")` |
|--------|-------------------|------------------|
| 头文件 | `<string.h>` | `<stdio.h>` |
| 输出方式 | 返回字符串，需自己 `printf` | 直接打印到 stderr |
| 典型用法 | 日志、自定义格式 | **调试首选** |

#### 示例代码 3.2.1 strerror

```c
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdio.h>
#include <errno.h>
#include <string.h>

int main(void)
{
    int fd;

    fd = open("./test_file", O_RDONLY);
    if (-1 == fd) {
        printf("Error: %s\n", strerror(errno));
        return -1;
    }
    close(fd);
    return 0;
}
```

![图 3.2.2](images/figures/corrected/fig-3-2-2.png)

#### 示例代码 3.2.2 perror

```c
    fd = open("./test_file", O_RDONLY);
    if (-1 == fd) {
        perror("open error");
        return -1;
    }
```

![图 3.2.3](images/figures/corrected/fig-3-2-3.png)

---

## 3.3 exit、_exit、_Exit

### 四种正常退出方式对比

| 方式 | 类型 | 是否刷新 stdio | 是否调 C 库清理 | 典型场景 |
|------|------|:--------------:|:---------------:|----------|
| `return`（main） | — | 会（经 exit 路径） | 会 | main 正常结束 |
| `exit(status)` | C 库 | **会** | **会** | 应用层推荐 |
| `_exit(status)` | 系统调用 | 否 | 否 | 子进程、已知不需刷缓冲 |
| `_Exit(status)` | 系统调用 | 否 | 否 | 与 `_exit` 等价 |

#### 示例代码 3.3.1 _exit

```c
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdio.h>

int main(void)
{
    int fd;

    fd = open("./test_file", O_RDONLY);
    if (-1 == fd) {
        perror("open error");
        _exit(-1);
    }
    close(fd);
    _exit(0);
}
```

---

## 3.4 空洞文件（Sparse File）

- `lseek` 可把偏移设到**超过当前文件长度**；中间未写区域 = **空洞**。
- **逻辑大小**（`ls`）含空洞；**物理占用**（`du`）不含，写入后才分配块。

```
[0~4095] 空洞  →  [4096~8191] 实际数据  →  ls≈8K, du≈4K
```

#### 示例代码 3.4.1

```c
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

int main(void)
{
    int fd, ret;
    char buffer[1024];
    int i;

    fd = open("./hole_file", O_WRONLY | O_CREAT | O_EXCL,
             S_IRUSR | S_IWUSR | S_IRGRP | S_IROTH);
    if (-1 == fd) {
        perror("open error");
        exit(-1);
    }

    ret = lseek(fd, 4096, SEEK_SET);
    if (-1 == ret) {
        perror("lseek error");
        goto err;
    }

    memset(buffer, 0xFF, sizeof(buffer));
    for (i = 0; i < 4; i++) {
        ret = write(fd, buffer, sizeof(buffer));
        if (-1 == ret) {
            perror("write error");
            goto err;
        }
    }

    ret = 0;
err:
    close(fd);
    exit(ret);
}
```

![示例 3.4.2 ls/du 结果](images/figures/corrected/fig-3-4-1.png)

> **思考题**：`read` 空洞区读到什么？需自行实验（常为 `0x00`）。

---

## 3.5 O_APPEND 与 O_TRUNC

### O_TRUNC 与「截断函数」的区别（易混）

| 对比项 | `O_TRUNC`（open 标志） | `truncate` / `ftruncate`（见 3.11） |
|--------|------------------------|-------------------------------------|
| 时机 | **打开瞬间**清空 | 文件已打开后/用路径随时截断 |
| 接口 | `open(..., O_TRUNC)` | `truncate(path,len)` / `ftruncate(fd,len)` |
| 长度 | 变为 0 | 可设为任意 `length` |

#### 示例代码 3.5.1 O_TRUNC

```c
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>

int main(void)
{
    int fd;

    fd = open("./test_file", O_WRONLY | O_TRUNC);
    if (-1 == fd) {
        perror("open error");
        exit(-1);
    }
    close(fd);
    exit(0);
}
```

![图 3.5.1](images/figures/corrected/fig-3-5-1.png)  
*打开前 8760 字节 → 仅 open+close 后变为 0*

### O_APPEND 要点

| 对比项 | 写操作 | 读操作 |
|--------|--------|--------|
| 偏移 | 每次 `write` 前自动移到**文件尾** | **不影响**，默认仍可从文件头读 |
| `lseek` | **不能**改变写偏移（write 仍落末尾） | 可正常 `lseek` 后 read |

#### 示例代码 3.5.2 O_APPEND

```c
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void)
{
    char buffer[16];
    int fd, ret;

    fd = open("./test_file", O_RDWR | O_APPEND);
    if (-1 == fd) {
        perror("open error");
        exit(-1);
    }

    memset(buffer, 0x55, sizeof(buffer));
    ret = write(fd, buffer, 4);
    if (-1 == ret) {
        perror("write error");
        goto err;
    }

    memset(buffer, 0x00, sizeof(buffer));
    ret = lseek(fd, -4, SEEK_END);
    if (-1 == ret) {
        perror("lseek error");
        goto err;
    }

    ret = read(fd, buffer, 4);
    if (-1 == ret) {
        perror("read error");
        goto err;
    }

    printf("0x%x 0x%x 0x%x 0x%x\n",
           buffer[0], buffer[1], buffer[2], buffer[3]);

    ret = 0;
err:
    close(fd);
    exit(ret);
}
```

![图 3.5.2](images/figures/corrected/fig-3-5-2.png)

**思考题**：`O_APPEND | O_TRUNC` → 先截断为 0，再追加写。

---

## 3.6 多次打开同一文件

### 核心结论对照

| 对比项 | 多次 `open` 同一文件 | `dup` / `dup2`（见 3.7） |
|--------|----------------------|-------------------------|
| fd 个数 | 多个 | 多个 |
| 文件表 | **多个**（各一条） | **同一表项** |
| 读写偏移 | **相互独立** | **共享** |
| 动态文件（内存） | **一份** | **一份** |
| 默认写方式 | 分别写（易覆盖） | 接续写 |
| 接续写办法 | 两 fd 都加 `O_APPEND` | 直接交替 write |

#### 示例代码 3.6.1 三个 fd

```c
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>

int main(void)
{
    int fd1, fd2, fd3;
    int ret;

    fd1 = open("./test_file", O_RDWR);
    if (-1 == fd1) { perror("open error"); exit(-1); }

    fd2 = open("./test_file", O_RDWR);
    if (-1 == fd2) { perror("open error"); ret = -1; goto err1; }

    fd3 = open("./test_file", O_RDWR);
    if (-1 == fd3) { perror("open error"); ret = -1; goto err2; }

    printf("%d %d %d\n", fd1, fd2, fd3);

    close(fd3);
    ret = 0;
err2:
    close(fd2);
err1:
    close(fd1);
    exit(ret);
}
```

![图 3.6.1](images/figures/corrected/fig-3-6-1.png)

#### 示例代码 3.6.2 共享动态文件

```c
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void)
{
    char buffer[4];
    int fd1, fd2, ret;

    fd1 = open("./test_file", O_RDWR | O_CREAT | O_EXCL,
             S_IRUSR | S_IWUSR | S_IRGRP | S_IROTH);
    if (-1 == fd1) { perror("open error"); exit(-1); }

    fd2 = open("./test_file", O_RDWR);
    if (-1 == fd2) { perror("open error"); ret = -1; goto err1; }

    buffer[0] = 0x11; buffer[1] = 0x22;
    buffer[2] = 0x33; buffer[3] = 0x44;
    write(fd1, buffer, 4);

    lseek(fd2, 0, SEEK_SET);
    memset(buffer, 0x00, sizeof(buffer));
    read(fd2, buffer, 4);
    printf("0x%x 0x%x 0x%x 0x%x\n",
           buffer[0], buffer[1], buffer[2], buffer[3]);

    ret = 0;
err1:
    close(fd2);
    close(fd1);
    exit(ret);
}
```

![图 3.6.2](images/figures/corrected/fig-3-6-2.png)

![图 3.6.3 数据结构](images/figures/corrected/fig-3-6-3.png)

#### 示例代码 3.6.3 分别写（无 O_APPEND）

```c
/* 与 3.6.2 相同 open 方式；buffer1=0x11..44, buffer2=0xAA..DD */
for (i = 0; i < 4; i++) {
    write(fd1, buffer1, sizeof(buffer1));
    write(fd2, buffer2, sizeof(buffer2));
}
lseek(fd1, 0, SEEK_SET);
for (i = 0; i < 8; i++) {
    read(fd1, buffer1, sizeof(buffer1));
    printf("%x%x%x%x", buffer1[0], buffer1[1], buffer1[2], buffer1[3]);
}
/* 输出 aabbccdd... */
```

![图 3.6.4](images/figures/corrected/fig-3-6-4.png)

#### 示例代码 3.6.4 接续写（双 O_APPEND）

```c
fd1 = open("./test_file", O_RDWR | O_CREAT | O_EXCL | O_APPEND,
          S_IRUSR | S_IWUSR | S_IRGRP | S_IROTH);
fd2 = open("./test_file", O_RDWR | O_APPEND);
/* 循环写同上 → 读出 11223344aabbccdd... */
```

![图 3.6.5](images/figures/corrected/fig-3-6-5.png)

- **跨进程**：多进程 `open` 同一文件 → 共享一份动态文件，**偏移仍独立**。
- **引用计数**：文件表记录；所有 fd `close` 且计数为 0 才释放动态缓存。

---

## 3.7 复制文件描述符 dup / dup2

```c
#include <unistd.h>
int dup(int oldfd);
int dup2(int oldfd, int newfd);
```

### dup / dup2 / fcntl(F_DUPFD) 对比

| 对比项 | `dup` | `dup2` | `fcntl(fd, F_DUPFD, min)` |
|--------|-------|--------|---------------------------|
| 新 fd 编号 | 系统分配最小可用 | **调用者指定** `newfd` | ≥ `min` 的最小可用 |
| 共享文件表 | 是 | 是 | 是 |
| 共享偏移 | 是 | 是 | 是 |
| 失败时 | -1 | -1（newfd 非法或占用） | -1 |

![图 3.7.1](images/figures/corrected/fig-3-7-1.png)

#### 示例代码 3.7.1 dup 接续写

```c
/* 与 3.6.3 结构相同，区别：fd2 = dup(fd1); 无 O_APPEND 也能接续写 */
fd1 = open("./test_file", O_RDWR | O_CREAT | O_EXCL, 0664);
fd2 = dup(fd1);
/* 循环 write(fd1,buffer1); write(fd2,buffer2); 再 read 验证 */
```

![图 3.7.2](images/figures/corrected/fig-3-7-2.png)

#### 示例代码 3.7.2 dup2 指定 fd

```c
fd2 = dup2(fd1, 100);   /* 新 fd 必为 100（若未被占用） */
printf("fd1: %d\nfd2: %d\n", fd1, fd2);
```

![图 3.7.3](images/figures/corrected/fig-3-7-3.png)

---

## 3.8 文件共享

**定义**：同一 **inode** 被多个读写体同时 I/O。

| 实现方式 | 共享偏移？ | 示意图 |
|----------|:----------:|--------|
| 同进程多次 open | 否 | 图 3.8.1 |
| 不同进程 open | 否 | 图 3.8.2 |
| dup / dup2 | **是** | 图 3.8.3 |

![图 3.8.1](images/figures/corrected/fig-3-8-1.png)  
![图 3.8.2](images/figures/corrected/fig-3-8-2.png)  
![图 3.8.3](images/figures/corrected/fig-3-8-3.png)

---

## 3.9 原子操作与竞争冒险

### 竞争冒险

「`lseek` 到末尾」+「`write`」是两步，多进程交错 → 覆盖（图 3.9.1）。

![图 3.9.1](images/figures/corrected/fig-3-9-1.png)

### 三种原子化手段对比

| 手段 | 原子了什么 | 与 read+lseek 对比 |
|------|------------|-------------------|
| `O_APPEND` | write 内「移到尾+写」 | 仅影响写 |
| `pread`/`pwrite` | 带 offset 的一次读写 | **不改变** fd 当前偏移 |
| `O_CREAT\|O_EXCL` | 不存在才创建 | 防双创建 |

### pread / pwrite 与 lseek+read/write

| 对比项 | `read` + `lseek` | `pread` |
|--------|------------------|---------|
| 步骤 | 两步，可被打断 | 一步 |
| 调用后当前偏移 | **会改变** | **不改变**（教材验证仍为 0） |

#### 示例代码 3.9.1 pread

```c
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>

int main(void)
{
    unsigned char buffer[100];
    int fd, ret;

    fd = open("./test_file", O_RDWR);
    if (-1 == fd) {
        perror("open error");
        exit(-1);
    }

    ret = pread(fd, buffer, sizeof(buffer), 1024);
    if (-1 == ret) {
        perror("pread error");
        goto err;
    }

    ret = lseek(fd, 0, SEEK_CUR);
    if (-1 == ret) {
        perror("lseek error");
        goto err;
    }
    printf("Current Offset: %d\n", ret);

    ret = 0;
err:
    close(fd);
    exit(ret);
}
```

![图 3.9.2](images/figures/corrected/fig-3-9-2.png)  
*打印 Current Offset: 0*

![图 3.9.3 O_EXCL](images/figures/corrected/fig-3-9-3.png)

正确创建：`open(path, O_RDWR | O_CREAT | O_EXCL, mode)`。

---

## 3.10 fcntl 与 ioctl

```c
#include <fcntl.h>
int fcntl(int fd, int cmd, ...);
```

| cmd | 作用 |
|-----|------|
| `F_DUPFD` | 复制 fd，第三参为最小新 fd |
| `F_GETFD` / `F_SETFD` | 描述符标志（如 FD_CLOEXEC） |
| `F_GETFL` / `F_SETFL` | 文件状态标志（如事后加 `O_APPEND`） |

**F_SETFL 限制**：只能改 `O_APPEND、O_NONBLOCK、O_DIRECT` 等；**不能**改 `O_RDONLY` 或 `O_CREAT/O_TRUNC`。

#### 示例代码 3.10.1 F_DUPFD

```c
fd1 = open("./test_file", O_RDONLY);
fd2 = fcntl(fd1, F_DUPFD, 0);
printf("fd1: %d\nfd2: %d\n", fd1, fd2);
```

![图 3.10.1](images/figures/corrected/fig-3-10-1.png)

#### 示例代码 3.10.2 F_SETFL 添加 O_APPEND

```c
flag = fcntl(fd, F_GETFL);
printf("flags: 0x%x\n", flag);
fcntl(fd, F_SETFL, flag | O_APPEND);
```

![图 3.10.2](images/figures/corrected/fig-3-10-2.png)

**ioctl**：设备专用控制，进阶篇再学。

---

## 3.11 截断文件 truncate / ftruncate

```c
#include <unistd.h>
#include <sys/types.h>

int truncate(const char *path, off_t length);
int ftruncate(int fd, off_t length);
```

### truncate 与 ftruncate 对比（重点）

| 对比项 | `truncate(path, length)` | `ftruncate(fd, length)` |
|--------|--------------------------|-------------------------|
| **如何指定文件** | 字符串 **路径 path** | 已打开的 **文件描述符 fd** |
| 是否需要先 `open` | **不需要** | **必须先** `open` 得到 fd |
| 写权限要求 | 对路径有写权限即可 | `open` 时需 `O_WRONLY` 或 `O_RDWR` |
| 截断语义 | **完全相同** | **完全相同** |
| 头文件 | `<unistd.h>`、`<sys/types.h>` | 同上 |

### length 参数语义

| 情况 | 结果 |
|------|------|
| `length` < 当前大小 | 截断，后面数据丢失 |
| `length` > 当前大小 | **扩展**；扩展区读为 `'\0'`（类似空洞） |
| 当前读写偏移 | **截断不改变** offset；文件变短后旧 offset 可能越界 → 需 `lseek` 重设 |

### 与 O_TRUNC、空洞文件的关系

| 手段 | 典型结果长度 |
|------|--------------|
| `open(..., O_TRUNC)` | 固定变为 **0** |
| `ftruncate(fd, 0)` | 变为 **0**（需已有 fd） |
| `truncate(path, 1024)` | 变为 **1024**（可扩展） |
| `lseek` 超 EOF 再写 | 产生**空洞**（逻辑大、物理小） |

#### 示例代码 3.11.1（教材完整）

```c
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>

int main(void)
{
    int fd;

    /* 打开 file1 → 用 fd 截断 */
    if (0 > (fd = open("./file1", O_RDWR))) {
        perror("open error");
        exit(-1);
    }

    /* ftruncate：通过文件描述符，截为 0 字节 */
    if (0 > ftruncate(fd, 0)) {
        perror("ftruncate error");
        exit(-1);
    }

    /* truncate：通过路径，截为 1024 字节 */
    if (0 > truncate("./file2", 1024)) {
        perror("truncate error");
        exit(-1);
    }

    close(fd);
    exit(0);
}
```

![图 3.11.1 截断前](images/figures/corrected/fig-3-11-1.png)  
![图 3.11.2 截断后 file1=0, file2=1024](images/figures/corrected/fig-3-11-2.png)

---

## 第 3 章易混点速查

| # | 易混 | 区分要点 |
|---|------|----------|
| 1 | `ls` vs `du` | 逻辑大小 vs 物理块占用 |
| 2 | `O_TRUNC` vs `truncate` | open 时清空 vs 已打开后按 length 截断 |
| 3 | `truncate` vs `ftruncate` | **path** vs **fd** |
| 4 | 多次 open vs dup | 多文件表/独立偏移 vs 共享表/共享偏移 |
| 5 | `O_APPEND` vs 手动 `lseek` 到尾 | 仅 write 强制末尾；lseek 改不了写位置 |
| 6 | `pread` vs `read+lseek` | 不改当前偏移；更原子 |
| 7 | `exit` vs `_exit` | 刷 stdio vs 不刷 |
| 8 | `strerror` vs `perror` | 返回串 vs 直接打印 |
| 9 | `dup` vs `dup2` vs `F_DUPFD` | 自动 fd / 指定 fd / 指定最小 fd |

---

## 自测清单

- [ ] 画出 fd → 文件表 → inode → block  
- [ ] 说明快速格式化为何可恢复  
- [ ] 默写 3.11.1，说清 `truncate` 与 `ftruncate` 唯一差别  
- [ ] 跑通 3.6.3 与 3.6.4，解释分别写与接续写  
- [ ] 用 dup 实现接续写，对比双 open  
- [ ] `pread` 后 `lseek(SEEK_CUR)` 为何仍为 0  

---

*配图重生成：`python scripts/extract_figures.py`*
