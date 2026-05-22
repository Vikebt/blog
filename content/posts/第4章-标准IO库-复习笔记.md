# 第 4 章 标准 I/O 库 — 复习笔记

> **教材**：《I.MX6U 嵌入式 Linux C 应用编程指南》（正点原子）  
> **配图**：`images/figures/corrected/fig-4-x-x-x.png`

---

## 本章目录

4.1 简介 · 4.2 FILE 指针 · 4.3 标准流 · 4.4 fopen/fclose · 4.5 fread/fwrite  
4.6 fseek/ftell · 4.7 feof/ferror · 4.8 格式化 I/O · 4.9 缓冲 · 4.10 fileno/fdopen

---

## 4.1 标准 I/O 库简介

- 定义在 **`<stdio.h>`**，属于 **C 标准库**（非 Linux 独有系统调用）。
- 底层仍调用 `open/read/write/close` 等，但在用户态增加 **stdio 缓冲区**、块长度优化。
- **优势**：可移植性好、API 简单、多数顺序读写场景 **更少系统调用、更快**。

---

## 4.2 FILE 指针

| 对比项 | 文件 I/O | 标准 I/O |
|--------|----------|----------|
| 句柄类型 | `int fd` | `FILE *` |
| 结构体 | 无（内核维护表项） | `struct _IO_FILE`（含真实 fd、缓冲指针、长度、错误标志等） |
| 头文件 | `<fcntl.h>` `<unistd.h>` | `<stdio.h>` |

---

## 4.3 标准输入、标准输出、标准错误

| 流 | fd（unistd.h） | FILE*（stdio.h） | 默认设备 | 缓冲倾向 |
|----|----------------|------------------|----------|----------|
| 标准输入 | `0` `STDIN_FILENO` | `stdin` | 键盘 | 终端常**行缓冲** |
| 标准输出 | `1` `STDOUT_FILENO` | `stdout` | 终端 | 终端常**行缓冲** |
| 标准错误 | `2` `STDERR_FILENO` | `stderr` | 终端 | 常**无缓冲** |

```c
#include <unistd.h>
#define STDIN_FILENO  0
#define STDOUT_FILENO 1
#define STDERR_FILENO 2

#include <stdio.h>
extern FILE *stdin, *stdout, *stderr;
```

---

## 4.4 fopen / fclose

```c
FILE *fopen(const char *path, const char *mode);
int fclose(FILE *stream);   /* 成功 0，失败 EOF(-1) */
```

### mode 含义（表 4.4.1）

| mode | 含义 | 文件不存在 | 文件已存在 |
|------|------|------------|------------|
| `r` | 只读 | 失败 | 打开，**不截断** |
| `r+` | 读写 | 失败 | 打开，不截断 |
| `w` | 只写 | **创建** | **截断为 0** |
| `w+` | 读写 | 创建 | 截断为 0 |
| `a` | 只写追加 | 创建 | 打开，写总在**末尾** |
| `a+` | 读写追加 | 创建 | 打开，写总在末尾 |

- `fopen` **不能**像 `open` 那样传权限位；新建默认 **`0666`**（再经 **umask** 掩码）。

```c
S_IRUSR | S_IWUSR | S_IRGRP | S_IWGRP | S_IROTH | S_IWOTH  /* 0666 */
```

#### 使用示例

```c
FILE *fp = fopen("./test_file", "w+");
if (fp == NULL) {
    perror("fopen error");
    exit(-1);
}
fclose(fp);
```

---

## 4.5 fread / fwrite

```c
size_t fread(void *ptr, size_t size, size_t nmemb, FILE *stream);
size_t fwrite(const void *ptr, size_t size, size_t nmemb, FILE *stream);
```

### fread/fwrite 与 read/write 对比

| 对比项 | `read` / `write` | `fread` / `fwrite` |
|--------|------------------|---------------------|
| 数据量参数 | 一个 `count`（字节数） | `size` × `nmemb`（数据项） |
| 返回值 | **字节数**（或 -1） | **数据项个数**（除非 size=1） |
| 缓冲 | 内核缓冲 | 内核 + **stdio 缓冲** |
| 到达末尾/错误 | 返回短计数 | 返回 < nmemb → 用 `feof`/`ferror` |

```c
fwrite(&obj, sizeof(struct mystr), 1, fp);
/* 等价 */
fwrite(&obj, 1, sizeof(struct mystr), fp);
```

#### 示例代码 4.5.1 fwrite

```c
#include <stdio.h>
#include <stdlib.h>

int main(void)
{
    char buf[] = "Hello World!\n";
    FILE *fp = NULL;

    if (NULL == (fp = fopen("./test_file", "w"))) {
        perror("fopen error");
        exit(-1);
    }
    printf("文件打开成功!\n");

    if (sizeof(buf) > fwrite(buf, 1, sizeof(buf), fp)) {
        printf("fwrite error\n");
        fclose(fp);
        exit(-1);
    }
    printf("数据写入成功!\n");

    fclose(fp);
    exit(0);
}
```

![图 4.5.1](images/figures/corrected/fig-4-5-1.png)

#### 示例代码 4.5.2 fread

```c
#include <stdio.h>
#include <stdlib.h>

int main(void)
{
    char buf[50] = {0};
    FILE *fp = NULL;
    int size;

    if (NULL == (fp = fopen("./test_file", "r"))) {
        perror("fopen error");
        exit(-1);
    }
    printf("文件打开成功!\n");

    if (12 > (size = fread(buf, 1, 12, fp))) {
        if (ferror(fp)) {
            printf("fread error\n");
            fclose(fp);
            exit(-1);
        }
        /* 未出错 → 已到文件末尾 */
    }
    printf("成功读取%d 个字节数据: %s\n", size, buf);

    fclose(fp);
    exit(0);
}
```

![图 4.5.2](images/figures/corrected/fig-4-5-2.png)

---

## 4.6 fseek / ftell

```c
int fseek(FILE *stream, long offset, int whence);
long ftell(FILE *stream);
```

### fseek 与 lseek 对比

| 对比项 | `fseek` | `lseek` |
|--------|---------|---------|
| 层次 | 标准 I/O | 系统调用 |
| 参数 | `FILE *` | `fd` |
| **成功返回值** | **0** | **新偏移量** |
| 失败 | -1 | -1 |
| whence | `SEEK_SET/SEEK_CUR/SEEK_END` | 同左 |

```c
fseek(fp, 0, SEEK_SET);
fseek(fp, 0, SEEK_END);
fseek(fp, 100, SEEK_SET);
```

#### 示例代码 4.6.1

```c
#include <stdio.h>
#include <stdlib.h>

int main(void)
{
    FILE *fp = NULL;
    char rd_buf[100] = {0};
    char wr_buf[] = "正点原子 http://www.openedv.com/forum.php\n";
    int ret;

    if (NULL == (fp = fopen("./test_file", "w+"))) {
        perror("fopen error");
        exit(-1);
    }
    printf("文件打开成功!\n");

    if (sizeof(wr_buf) > fwrite(wr_buf, 1, sizeof(wr_buf), fp)) {
        printf("fwrite error\n");
        fclose(fp);
        exit(-1);
    }
    printf("数据写入成功!\n");

    if (0 > fseek(fp, 0, SEEK_SET)) {
        perror("fseek error");
        fclose(fp);
        exit(-1);
    }

    if (sizeof(wr_buf) > (ret = fread(rd_buf, 1, sizeof(wr_buf), fp))) {
        printf("fread error\n");
        fclose(fp);
        exit(-1);
    }
    printf("成功读取%d 个字节数据: %s\n", ret, rd_buf);

    fclose(fp);
    exit(0);
}
```

![图 4.6.1](images/figures/corrected/fig-4-6-1.png)

#### 示例代码 4.6.2 用 ftell 求文件大小

```c
    if (NULL == (fp = fopen("./testApp.c", "r"))) {
        perror("fopen error");
        exit(-1);
    }
    fseek(fp, 0, SEEK_END);
    ret = ftell(fp);
    printf("文件大小: %d 个字节\n", ret);
    fclose(fp);
```

![图 4.6.2](images/figures/corrected/fig-4-6-2.png)

---

## 4.7 feof / ferror / clearerr

| 函数 | 检测对象 | 返回非 0 表示 |
|------|----------|---------------|
| `feof(fp)` | EOF 标志 | 已到文件尾 |
| `ferror(fp)` | 错误标志 | I/O 出错 |
| `clearerr(fp)` | 清除上述标志 | 无返回值 |

### fread 返回值不足时如何判断

| 顺序 | 做法 |
|------|------|
| 1 | `fread` 返回 < nmemb |
| 2 | 先 `ferror(fp)` → 真：错误 |
| 3 | 否则多为 **EOF**（可用 `feof` 确认） |

- **`fseek` 成功**也会清除 EOF 标志。

#### 示例代码 4.7.1

```c
#include <stdio.h>
#include <stdlib.h>

int main(void)
{
    FILE *fp = NULL;
    char buf[20] = {0};

    if (NULL == (fp = fopen("./testApp.c", "r"))) {
        perror("fopen error");
        exit(-1);
    }
    printf("文件打开成功!\n");

    if (0 > fseek(fp, 0, SEEK_END)) {
        perror("fseek error");
        fclose(fp);
        exit(-1);
    }

    if (10 > fread(buf, 1, 10, fp)) {
        if (feof(fp))
            printf("end-of-file 标志被设置,已到文件末尾!\n");
        clearerr(fp);
    }

    fclose(fp);
    exit(0);
}
```

---

## 4.8 格式化 I/O

### 输出五函数对比

| 函数 | 输出目标 |
|------|----------|
| `printf` | 标准输出 |
| `fprintf` | 指定 `FILE *` |
| `dprintf` | 指定 **fd** |
| `sprintf` | 用户缓冲区（有溢出风险） |
| `snprintf` | 用户缓冲区 + **长度限制**（推荐） |

### 输入三函数

`scanf` / `fscanf` / `sscanf` —— 格式串：`%[flags][width][.precision][length]type`

| 特性 | 说明 |
|------|------|
| `%*` | 读入但不存储 |
| `%ms` 等 `%m` | 库内 malloc，用完 **free** |
| width | 最大字段宽（如 `%4s`） |

格式表详见教材表 4.8.1~4.8.7。

#### 示例代码 4.8.1

```c
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>

int main(void)
{
    char buf[50] = {0};

    printf("%d (%s) %d (%s)\n", 520, "我爱你", 1314, "一生一世");
    fprintf(stdout, "%d (%s) %d (%s)\n", 520, "我爱你", 1314, "一生一世");
    dprintf(STDOUT_FILENO, "%d (%s) %d (%s)\n", 520, "我爱你", 1314, "一生一世");

    sprintf(buf, "%d (%s) %d (%s)\n", 520, "我爱你", 1314, "一生一世");
    printf("%s", buf);

    memset(buf, 0x00, sizeof(buf));
    snprintf(buf, sizeof(buf), "%d (%s) %d (%s)\n", 520, "我爱你", 1314, "一生一世");
    printf("%s", buf);

    exit(0);
}
```

![图 4.8.1](images/figures/corrected/fig-4-8-1.png)

#### 示例代码 4.8.2 scanf（%ms 需 free）

```c
    scanf("%d", &a);
    scanf("%f", &b);
    scanf("%ms", &str);   /* 库分配内存 */
    printf("你输入的字符串为: %s\n", str);
    free(str);
```

![图 4.8.2](images/figures/corrected/fig-4-8-2.png)

---

## 4.9 I/O 缓冲（全章重点）

### 4.9.1 内核缓冲与刷盘

`read/write` 先与 **内核 Page Cache** 交换，落盘由内核异步完成。

#### fsync / fdatasync / sync 对比

| 函数 | 范围 | 刷什么 | 何时返回（Linux） |
|------|------|--------|-------------------|
| `fsync(fd)` | 单文件 | **数据 + 元数据** | 该文件落盘完成后 |
| `fdatasync(fd)` | 单文件 | **仅数据** | 数据落盘完成后 |
| `sync()` | **全局** | 所有脏页 | 通常等写完才返回 |

#### open 同步标志

| 标志 | 近似效果 |
|------|----------|
| `O_SYNC` | 每次 `write` 后类似 `fsync` |
| `O_DSYNC` | 每次 `write` 后类似 `fdatasync` |

**U 盘**：拷贝后执行 `sync`，否则可能丢数据。

#### 示例代码 4.9.1 文件拷贝 + fsync

```c
#include <stdio.h>
#include <stdlib.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>

#define BUF_SIZE 4096
#define READ_FILE "./rfile"
#define WRITE_FILE "./wfile"

static char buf[BUF_SIZE];

int main(void)
{
    int rfd, wfd;
    size_t size;

    rfd = open(READ_FILE, O_RDONLY);
    wfd = open(WRITE_FILE, O_WRONLY | O_CREAT | O_TRUNC, 0664);

    while (0 < (size = read(rfd, buf, BUF_SIZE)))
        write(wfd, buf, size);

    fsync(wfd);   /* 确保目标文件落盘 */

    close(rfd);
    close(wfd);
    exit(0);
}
```

### 4.9.2 直接 I/O（O_DIRECT）

- `#define _GNU_SOURCE` 后 `open(..., O_DIRECT)`。
- **三条对齐**：缓冲区地址、文件偏移、读写长度均为 **块大小（常 4096）** 整数倍。

![图 4.9.1](images/figures/corrected/fig-4-9-1.png)  
![图 4.9.2 块大小](images/figures/corrected/fig-4-9-2.png)

#### 示例代码 4.9.2 直接 I/O（节选）

```c
#define _GNU_SOURCE
#include <fcntl.h>
#include <unistd.h>
/* 缓冲区需 __attribute__((aligned(4096))) */
fd = open("./test_file", O_WRONLY | O_CREAT | O_TRUNC | O_DIRECT, 0664);
while (count--)
    write(fd, buf, 4096);   /* 每次必须 4096 字节 */
```

![图 4.9.3](images/figures/corrected/fig-4-9-3.png)  
![图 4.9.4 普通 I/O 更快](images/figures/corrected/fig-4-9-4.png)

### 4.9.3 stdio 缓冲

```c
int setvbuf(FILE *stream, char *buf, int mode, size_t size);
```

#### 三种 stdio 缓冲模式

| mode | 名称 | 行为 |
|------|------|------|
| `_IONBF` | 无缓冲 | 每次 I/O 立刻进内核（**stderr** 默认） |
| `_IOLBF` | 行缓冲 | 遇 `\n` 刷（**终端 stdout** 默认） |
| `_IOFBF` | 全缓冲 | 缓冲满才 `write`（**磁盘文件** 默认） |

#### setvbuf / setbuf / setbuffer 对比

| 函数 | 指定缓冲大小 | 返回值 |
|------|:------------:|--------|
| `setvbuf` | **是**（参数 size） | 成功 0 |
| `setbuf` | 固定 `BUFSIZ` | void |
| `setbuffer` | **是** | void |

#### 刷新 stdio 的方式对比

| 方式 | 是否刷 stdio → 内核 |
|------|:-------------------:|
| `fflush(stream)` | **是** |
| `fclose` | **是** |
| `exit()` / `return` 正常结束 | **是** |
| `_exit()` | **否** |

#### 示例代码 4.9.4 行缓冲

```c
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

int main(void)
{
    printf("Hello World!\n");
    printf("Hello World!");
    for (;;)
        sleep(1);
}
```

![图 4.9.5 第二句不显示](images/figures/corrected/fig-4-9-5.png)

#### 示例代码 4.9.5 无缓冲

```c
    setvbuf(stdout, NULL, _IONBF, 0);
    printf("Hello World!\n");
    printf("Hello World!");
```

![图 4.9.6 两句都显示](images/figures/corrected/fig-4-9-6.png)

#### 示例代码 4.9.6 fflush

```c
    printf("Hello World!\n");
    printf("Hello World!");
    fflush(stdout);
```

![图 4.9.7](images/figures/corrected/fig-4-9-7.png)

#### 示例代码 4.9.8 程序退出自动刷

```c
    printf("Hello World!\n");
    printf("Hello World!");
    /* 无 fflush，直接结束 → 两句都会显示 */
```

![图 4.9.8](images/figures/corrected/fig-4-9-8.png)

### 两层缓冲总图

![图 4.9.9](images/figures/corrected/fig-4-9-9.png)

```
应用 → stdio 缓冲 → read/write → 内核缓冲 → 磁盘
         fflush              fsync/sync
```

---

## 4.10 文件描述符与 FILE 指针互转

```c
int fileno(FILE *stream);              /* FILE* → fd */
FILE *fdopen(int fd, const char *mode); /* fd → FILE*，mode 须与 open 方式一致 */
```

### 混合 I/O 注意

| 调用 | 走的缓冲 |
|------|----------|
| `printf` | stdio 缓冲 |
| `write(STDOUT_FILENO,...)` | **直接内核** |

#### 教材示例（先 write 后 print）

```c
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

int main(void)
{
    printf("print");
    write(STDOUT_FILENO, "write\n", 6);
    exit(0);
}
```

→ 常先看到 `write`，后看到 `print`；解决：`fflush(stdout)` 或统一用一种 I/O。

---

## 第 4 章易混点速查

| # | 易混 | 区分要点 |
|---|------|----------|
| 1 | `fread` 返回值 | **数据项个数**，不是字节数 |
| 2 | `fseek` vs `lseek` 成功返回 | **0** vs **新偏移** |
| 3 | `feof` vs `ferror` | 到末尾 vs 出错；先 `ferror` |
| 4 | `fsync` vs `fdatasync` | 数据+元数据 vs 仅数据 |
| 5 | `fflush` vs `fsync` | 只刷 stdio；落盘还要内核刷 |
| 6 | 行缓冲 vs 全缓冲 | 终端 `\n` vs 磁盘写满 |
| 7 | `sprintf` vs `snprintf` | 后者限长防溢出 |
| 8 | `exit` vs `_exit` 与 stdio | 前者刷缓冲，后者不刷 |
| 9 | `fileno` + `write` 混 `printf` | 双层缓冲顺序乱 |

---

## 自测清单

- [ ] 背诵六种 `fopen` mode 行为差异  
- [ ] 写 `fread` 分支：`ferror` / `feof`  
- [ ] `fseek`+`ftell` 求文件大小  
- [ ] 解释 4.9.5 第二个 printf 不显示  
- [ ] 列出 `fsync`/`fdatasync`/`sync` 区别  
- [ ] O_DIRECT 三条对齐  
- [ ] 运行 printf+write 实验并 `fflush` 修复  

---

*配图重生成：`python scripts/extract_figures.py`*
