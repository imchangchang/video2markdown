#!/usr/bin/env python3
"""Video2Markdown Batch Test Script

批量测试所有视频，生成详细报告和对比分析。

Usage:
    python scripts/batch_test.py [--stage1-only] [--parallel N]

Options:
    --stage1-only    只运行 Stage 1（快速测试视频分析）
    --parallel N     并行处理 N 个视频（默认 1，串行）
    --output DIR     指定输出目录
"""

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

# 配置
VIDEO_DIR = Path("testdata/videos")
DEFAULT_OUTPUT = Path("test_outputs/results") / f"batch_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
TIMEOUT_SECONDS = 600  # 10分钟超时

# 检测 uv 命令
def find_uv():
    """查找 uv 命令或虚拟环境 Python."""
    # 优先使用 uv
    result = subprocess.run(["which", "uv"], capture_output=True)
    if result.returncode == 0:
        return ["uv"]
    
    # 尝试虚拟环境
    venv_python = Path(".venv/bin/python")
    if venv_python.exists():
        return [str(venv_python), "-m"]
    
    # 尝试系统 Python
    result = subprocess.run(["which", "python3"], capture_output=True)
    if result.returncode == 0:
        return ["python3", "-m"]
    
    raise RuntimeError("未找到 uv 或 python 命令，请先安装 uv: https://github.com/astral-sh/uv")


def run_command(cmd: list[str], cwd: Optional[Path] = None) -> tuple[int, str, float]:
    """运行命令，返回 (exit_code, output, elapsed_seconds)."""
    start = time.time()
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=TIMEOUT_SECONDS
        )
        elapsed = time.time() - start
        return result.returncode, result.stdout + result.stderr, elapsed
    except subprocess.TimeoutExpired:
        elapsed = time.time() - start
        return 124, "Timeout", elapsed


def analyze_video_stage1(video_path: Path) -> dict:
    """只运行 Stage 1，获取视频分析结果."""
    print(f"  [Stage 1] 分析视频...")
    
    uv_cmd = find_uv()
    cmd = uv_cmd + [
        "run", "python", "-m", "video2markdown", "stage1",
        str(video_path)
    ]
    
    exit_code, output, elapsed = run_command(cmd)
    
    # 解析 Stage 1 输出
    result = {
        "exit_code": exit_code,
        "elapsed": elapsed,
        "duration": 0,
        "scene_changes": 0,
        "stable_intervals": 0,
        "unstable_intervals": 0,
        "stable_total": 0,
        "unstable_total": 0,
    }
    
    if exit_code == 0:
        # 从输出解析
        for line in output.split("\n"):
            if "时长:" in line:
                try:
                    result["duration"] = float(line.split("时长:")[1].split("s")[0].strip())
                except:
                    pass
            elif "场景变化:" in line:
                try:
                    result["scene_changes"] = int(line.split("检测到")[1].split("个")[0].strip())
                except:
                    pass
            elif "稳定区间:" in line:
                try:
                    parts = line.split("稳定区间:")[1].split("段")
                    result["stable_intervals"] = int(parts[0].strip())
                    result["stable_total"] = float(parts[1].split("(")[1].split("s")[0].strip())
                except:
                    pass
            elif "不稳定区间:" in line:
                try:
                    parts = line.split("不稳定区间:")[1].split("段")
                    result["unstable_intervals"] = int(parts[0].strip())
                    result["unstable_total"] = float(parts[1].split("(")[1].split("s")[0].strip())
                except:
                    pass
    
    return result


def process_video_full(video_path: Path, output_dir: Path) -> dict:
    """运行完整流程处理视频."""
    print(f"  [Full] 完整流程处理...")
    
    video_output = output_dir / video_path.stem
    video_output.mkdir(parents=True, exist_ok=True)
    
    uv_cmd = find_uv()
    cmd = uv_cmd + [
        "run", "python", "-m", "video2markdown", "process",
        str(video_path),
        "-o", str(video_output),
        "-l", "zh"
    ]
    
    exit_code, output, elapsed = run_command(cmd)
    
    # 保存日志
    log_file = video_output / "processing.log"
    log_file.write_text(output, encoding="utf-8")
    
    # 解析结果
    result = {
        "exit_code": exit_code,
        "elapsed": elapsed,
        "output_dir": str(video_output),
        "log_file": str(log_file),
    }
    
    # 统计关键帧
    if exit_code == 0:
        keep_count = output.count("KEEP")
        skip_count = output.count("SKIP")
        result["frames_keep"] = keep_count
        result["frames_skip"] = skip_count
    
    return result


def format_duration(seconds: float) -> str:
    """格式化时长."""
    if seconds < 60:
        return f"{seconds:.0f}s"
    else:
        return f"{int(seconds/60)}m {int(seconds%60)}s"


def generate_report(results: list[dict], output_dir: Path, stage1_only: bool):
    """生成测试报告."""
    report_file = output_dir / "summary.md"
    
    total = len(results)
    success = sum(1 for r in results if r.get("exit_code") == 0)
    failed = total - success
    
    lines = [
        "# Video2Markdown 批量测试报告",
        "",
        f"**测试时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**测试模式**: {'Stage 1 快速测试' if stage1_only else '完整流程'}",
        f"**视频目录**: {VIDEO_DIR}",
        f"**输出目录**: {output_dir}",
        "",
        "## 统计汇总",
        "",
        f"- **总视频数**: {total}",
        f"- **成功**: {success}",
        f"- **失败**: {failed}",
        f"- **成功率**: {success/total*100:.1f}%",
        "",
        "## 详细结果",
        "",
    ]
    
    if stage1_only:
        lines.append("| 序号 | 视频名称 | 时长 | 场景变化 | 稳定区间 | 不稳定区间 | 稳定占比 | 耗时 | 状态 |")
        lines.append("|-----|---------|------|---------|---------|-----------|---------|------|------|")
        
        for i, r in enumerate(results, 1):
            video_name = Path(r["video"]).name
            status = "✅ 成功" if r.get("exit_code") == 0 else "❌ 失败"
            if r.get("exit_code") == 124:
                status = "⏱️ 超时"
            
            stable_pct = ""
            if r.get("duration", 0) > 0:
                pct = r.get("stable_total", 0) / r.get("duration", 1) * 100
                stable_pct = f"{pct:.1f}%"
            
            lines.append(
                f"| {i} | {video_name[:30]}... | "
                f"{r.get('duration', 0):.1f}s | "
                f"{r.get('scene_changes', 0)} | "
                f"{r.get('stable_intervals', 0)} ({r.get('stable_total', 0):.1f}s) | "
                f"{r.get('unstable_intervals', 0)} ({r.get('unstable_total', 0):.1f}s) | "
                f"{stable_pct} | "
                f"{format_duration(r.get('elapsed', 0))} | "
                f"{status} |"
            )
    else:
        lines.append("| 序号 | 视频名称 | 时长 | 保留帧 | 跳过帧 | 总耗时 | 状态 |")
        lines.append("|-----|---------|------|-------|-------|-------|------|")
        
        for i, r in enumerate(results, 1):
            video_name = Path(r["video"]).name
            status = "✅ 成功" if r.get("exit_code") == 0 else "❌ 失败"
            if r.get("exit_code") == 124:
                status = "⏱️ 超时"
            
            lines.append(
                f"| {i} | {video_name[:30]}... | "
                f"{r.get('duration', 0):.1f}s | "
                f"{r.get('frames_keep', 0)} | "
                f"{r.get('frames_skip', 0)} | "
                f"{format_duration(r.get('elapsed', 0))} | "
                f"{status} |"
            )
    
    lines.extend([
        "",
        "## 失败详情",
        "",
    ])
    
    failed_results = [r for r in results if r.get("exit_code") != 0]
    if failed_results:
        for r in failed_results:
            lines.append(f"- **{Path(r['video']).name}**: 退出码 {r.get('exit_code')}")
    else:
        lines.append("无失败记录 🎉")
    
    report_file.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n报告已生成: {report_file}")


def main():
    parser = argparse.ArgumentParser(description="Video2Markdown 批量测试")
    parser.add_argument("--stage1-only", action="store_true", help="只运行 Stage 1（快速测试）")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="输出目录")
    args = parser.parse_args()
    
    # 创建输出目录
    args.output.mkdir(parents=True, exist_ok=True)
    
    # 获取所有视频
    videos = sorted(VIDEO_DIR.glob("*.mp4"))
    if not videos:
        print(f"错误: 未在 {VIDEO_DIR} 找到视频文件")
        sys.exit(1)
    
    print("=" * 60)
    print("Video2Markdown 批量测试")
    print("=" * 60)
    print(f"\n发现 {len(videos)} 个视频")
    print(f"输出目录: {args.output}")
    print(f"测试模式: {'Stage 1 快速测试' if args.stage1_only else '完整流程'}")
    print("")
    
    # 处理每个视频
    results = []
    start_time = time.time()
    
    for i, video_path in enumerate(videos, 1):
        print(f"\n[{i}/{len(videos)}] {video_path.name}")
        
        result = {"video": str(video_path)}
        
        # 先运行 Stage 1 获取基本信息
        stage1_result = analyze_video_stage1(video_path)
        result.update(stage1_result)
        
        # 如果需要完整流程
        if not args.stage1_only and stage1_result.get("exit_code") == 0:
            full_result = process_video_full(video_path, args.output)
            result.update(full_result)
        
        results.append(result)
        
        # 打印简要结果
        status = "✓" if result.get("exit_code") == 0 else "✗"
        elapsed = format_duration(result.get("elapsed", 0))
        print(f"  结果: {status} 耗时: {elapsed}")
    
    total_elapsed = time.time() - start_time
    
    # 生成报告
    generate_report(results, args.output, args.stage1_only)
    
    # 打印总结
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
    print(f"总视频数: {len(videos)}")
    print(f"成功: {sum(1 for r in results if r.get('exit_code') == 0)}")
    print(f"失败: {sum(1 for r in results if r.get('exit_code') != 0)}")
    print(f"总耗时: {format_duration(total_elapsed)}")
    print(f"报告文件: {args.output}/summary.md")


if __name__ == "__main__":
    main()
