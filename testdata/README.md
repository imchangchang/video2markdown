# Test Data 目录

此目录存放测试数据，**不纳入 Git 版本控制**。

## 目录结构

```
testdata/
├── videos/               # 大型测试视频（手动放置）
│   ├── sample_short.mp4  # 短视频（<30秒，用于快速测试）
│   └── sample_long.mp4   # 长视频（用于完整测试）
└── samples/              # 小型样本数据
    └── README.md
```

## 使用方法

### 放置测试视频

```bash
# 复制或链接测试视频
cp /path/to/your/video.mp4 testdata/videos/sample_short.mp4

# 或使用软链接（节省空间）
ln -s /path/to/your/video.mp4 testdata/videos/sample_long.mp4
```

### 在测试中使用

```python
def test_with_video(get_test_video):
    video_path = get_test_video
    # video_path 指向 testdata/videos/ 中的第一个视频
```

## 视频建议

| 用途 | 建议时长 | 建议大小 | 文件名 |
|------|---------|---------|--------|
| 单元测试 | <10秒 | <5MB | sample_tiny.mp4 |
| 快速集成测试 | 30秒-2分钟 | <50MB | sample_short.mp4 |
| 完整流程测试 | 5-30分钟 | <500MB | sample_long.mp4 |

## Git LFS（可选）

如果希望将测试视频纳入版本控制，可以使用 Git LFS：

```bash
# 安装 Git LFS
git lfs install

# 跟踪视频文件
git lfs track "testdata/videos/*.mp4"
git lfs track "testdata/videos/*.avi"

# 提交 .gitattributes
git add .gitattributes
git commit -m "Setup Git LFS for test videos"

# 现在可以正常添加视频了
git add testdata/videos/sample_short.mp4
git commit -m "Add test video"
```

**注意**：Git LFS 需要额外的存储空间，小团队可以手动管理视频文件。
