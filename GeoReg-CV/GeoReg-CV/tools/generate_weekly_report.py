from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt


OUTPUT = Path(r"C:\Users\V\Desktop\GeoReg-CV课题周报_方向更新后阶段总结_2026-08-15.docx")


def set_run_font(run, size=11, bold=False):
    run.font.name = "宋体"
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")
    run.font.size = Pt(size)
    run.bold = bold


def add_paragraph(document, text="", bold_prefix=None):
    paragraph = document.add_paragraph()
    paragraph.paragraph_format.space_after = Pt(4)
    paragraph.paragraph_format.line_spacing = 1.25
    if bold_prefix and text.startswith(bold_prefix):
        first = paragraph.add_run(bold_prefix)
        set_run_font(first, bold=True)
        rest = paragraph.add_run(text[len(bold_prefix):])
        set_run_font(rest)
    else:
        run = paragraph.add_run(text)
        set_run_font(run)
    return paragraph


def add_bullet(document, text):
    paragraph = document.add_paragraph(style="List Bullet")
    paragraph.paragraph_format.space_after = Pt(2)
    paragraph.paragraph_format.line_spacing = 1.2
    set_run_font(paragraph.add_run(text))


def add_heading(document, text, level=1):
    paragraph = document.add_heading(level=level)
    paragraph.paragraph_format.space_before = Pt(8)
    paragraph.paragraph_format.space_after = Pt(4)
    run = paragraph.add_run(text)
    set_run_font(run, size=14 if level == 1 else 12, bold=True)


def set_cell_text(cell, text, bold=False):
    cell.text = ""
    paragraph = cell.paragraphs[0]
    set_run_font(paragraph.add_run(str(text)), size=10, bold=bold)


def add_table(document, headers, rows):
    table = document.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    for index, header in enumerate(headers):
        set_cell_text(table.rows[0].cells[index], header, bold=True)
    for row in rows:
        cells = table.add_row().cells
        for index, value in enumerate(row):
            set_cell_text(cells[index], value)
    document.add_paragraph()


def build_document():
    document = Document()
    section = document.sections[0]
    section.top_margin = Cm(2.2)
    section.bottom_margin = Cm(2.2)
    section.left_margin = Cm(2.4)
    section.right_margin = Cm(2.4)

    title = document.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_run_font(title.add_run("GeoReg-CV课题周报"), size=18, bold=True)
    subtitle = document.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_run_font(subtitle.add_run("方向更新后阶段工作总结（截至2026年8月15日）"), size=11)

    add_heading(document, "一、本阶段工作概述")
    add_paragraph(
        document,
        "课题方向已由以University-1652图像检索为主的轻量化研究，更新为“面向观察员—无人机协同感知的跨平台空间配准方法研究”。当前以AnyVisLoc作为正式baseline和数据基础，输入观察者/低空斜视图像，在无人机航拍参考图中完成候选区域检索、跨视角特征匹配和PnP几何定位，最终输出场景局部空间位置、定位置信度、运行路径和可视化结果。",
    )

    add_heading(document, "二、当前技术路线")
    add_paragraph(
        document,
        "观察者视角图像 → CAMP航拍区域检索 → RoMa跨视角特征匹配 → P3P/PnP几何定位 → CDA-FastReg置信度判断 → 输出估计位置、误差、日志和可视化结果。",
    )
    add_paragraph(
        document,
        "官方AnyVisLoc工程保留在D:\\GD\\Benchmark，课题工程位于D:\\GeoReg-CV。当前所有新增系统功能均在GeoReg-CV中完成，没有修改官方工程。",
    )

    add_heading(document, "三、已完成工作")
    add_heading(document, "1. 建立独立GeoReg-CV课题工程", level=2)
    for text in (
        "建立configs、datasets、views、registration、system、pipelines、visualization、tools、experiments、outputs和docs等模块。",
        "完成AnyVisLoc数据适配、观察者视角与航拍参考视角抽象、统一定位结果结构、CSV/JSON输出和仿真数据接口。",
        "形成baseline运行、结果分析、系统演示、单样本定位和CDA-FastReg在线运行入口。",
    ):
        add_bullet(document, text)

    add_heading(document, "2. 完成AnyVisLoc Scene_01全量baseline复现", level=2)
    add_table(
        document,
        ["指标", "结果"],
        [
            ["测试样本数", "1846"],
            ["PnP成功数", "1846"],
            ["Mean Error", "7.8665 m"],
            ["Median Error", "0.4773 m"],
            ["Success@1m", "87.27%"],
            ["Success@3m", "99.02%"],
            ["Success@5m", "99.51%"],
            ["Success@10m / 20m", "99.62% / 99.62%"],
            ["Recall@5", "95.07%"],
            ["平均耗时", "约21.12 s/样本"],
            ["总耗时", "约11小时43分钟"],
        ],
    )
    add_paragraph(
        document,
        "全量结果已冻结归档，并完成成功/失败样本筛选、误差统计、定位位置对比和分析报告。",
    )

    add_heading(document, "3. 完成快速配置消融", level=2)
    add_table(
        document,
        ["配置", "平均耗时", "Mean Error", "Success@5m"],
        [
            ["Standard Top5", "23.72 s", "4.392 m", "98.33%"],
            ["Fast-v1", "21.73 s", "9.008 m", "96.67%"],
            ["Fast-v3", "22.32 s", "4.872 m", "99.17%"],
            ["Fast-v2 Top1", "16.42 s", "90.687 m", "91.67%"],
        ],
    )
    add_paragraph(
        document,
        "实验表明固定Top1虽然速度较快，但严重错误样本明显增加，因此需要根据匹配置信度动态决定是否增加候选区域。",
    )

    add_heading(document, "4. 提出并实现CDA-FastReg", level=2)
    add_paragraph(
        document,
        "CDA-FastReg（Confidence-Driven Adaptive Fast Registration）首先执行Top1快速定位；当PnP失败或Top1内点数低于阈值1000时，再回退到Top2或Top5。在线决策只使用PnP成功状态和内点数，不使用真实位置或定位误差。",
    )
    add_paragraph(
        document,
        "在前120个样本的离线模拟中，Top1快速路径占110个样本，回退10个样本，Success@5m为99.17%，估算平均耗时17.43 s，相对Standard Top5约加速1.36倍。",
    )

    add_heading(document, "5. 完成指定AnyVisLoc样本输入", level=2)
    add_paragraph(
        document,
        "目前可通过scene和sample-id明确指定数据集中的一张图片，例如Scene_01/L01_0120。系统会自动读取对应NPZ中的图像、相机内参、畸变参数、高度和姿态，并完成检索、匹配与定位。",
    )
    add_paragraph(document, "推荐运行命令：")
    add_paragraph(
        document,
        "python -u pipelines\\run_online_cda_sample.py --sample-id L01_0120 --scene Scene_01 --fallback-topk 5",
    )

    add_heading(document, "6. 完成单进程模型复用优化", level=2)
    add_paragraph(
        document,
        "将原先Top1和fallback分别启动进程的方式，改为CAMP和RoMa只初始化一次、参考图只读取一次、检索只执行一次。Top1置信度不足时，仅继续匹配候选2至N，不重新匹配候选1。",
    )
    add_table(
        document,
        ["验证样本", "执行路径", "定位误差", "墙钟时间"],
        [
            ["L01_0001", "Top1直接通过", "0.469 m", "21.53 s"],
            ["L01_0120（旧两进程）", "Top1→Top5", "0.432 m", "73.34 s"],
            ["L01_0120（单进程复用）", "Top1→Top5", "约0.45 m", "29.42 s"],
        ],
    )
    add_paragraph(
        document,
        "回退样本总耗时由73.34 s降至29.42 s，约加速2.49倍，耗时降低约59.9%。",
    )

    add_heading(document, "7. 接入完整单样本输出与可视化", level=2)
    for text in (
        "cda_result.json/csv：估计位置、真实位置、误差、内点数、CDA路径和模块耗时。",
        "online_cda.log：完整控制台运行日志。",
        "VG_data_<sample>.pkl：检索、匹配、PnP和自适应路径的完整中间数据。",
        "localization_panel.png：观察者图、候选检索图、最佳PnP匹配图、位置图和指标汇总。",
        "position_map.png：航拍参考图上的真实位置、估计位置和误差连线。",
        "1_Retrieval.jpg及pnp_inliers图片：检索候选和各候选区域的几何内点匹配结果。",
    ):
        add_bullet(document, text)

    add_heading(document, "四、当前系统状态")
    add_paragraph(
        document,
        "当前系统已经能够完成“指定AnyVisLoc观察者图像 → 航拍区域检索 → 自适应跨视角匹配 → PnP定位 → 输出空间位置 → 保存完整可视化”的闭环流程。",
    )
    add_paragraph(
        document,
        "需要说明：当前输出位置是AnyVisLoc场景局部米制坐标，不是经纬度；当前输入支持数据集中的指定NPZ样本，尚未直接支持缺少相机参数的任意外部JPG/PNG图片。",
    )

    add_heading(document, "五、阶段性发现")
    for text in (
        "Top1内点数可以作为在线置信度依据，但低内点回退到真正Top2后不一定恢复正确定位，复杂样本可能需要Top5。",
        "历史目录fast_v3_top2中的retrieval_k=2只是评价设置，实际运行仍匹配了5个候选；当前新入口中的fallback-topk 2才是真正Top2。",
        "模型初始化、参考图准备和检索仍占单样本总耗时的主要部分，后续批量运行可进一步通过跨样本缓存降低平均耗时。",
    ):
        add_bullet(document, text)

    add_heading(document, "六、下一步工作")
    for text in (
        "在更多Scene_01样本上运行单进程在线CDA-FastReg，重新统计真实在线速度、成功率和回退比例。",
        "根据在线结果重新标定内点阈值，并对Top2和Top5回退策略进行正式对比。",
        "实现二维交互式仿真界面，读取现有JSON结果并播放真实位置、估计位置和CDA路由。",
        "补充模块耗时表、方法流程图、消融实验表和论文方法章节。",
        "后续根据展示需求，再评估Unity三维场景或外部相机图片输入。",
    ):
        add_bullet(document, text)

    add_heading(document, "七、主要文件位置")
    locations = [
        ("课题工程", r"D:\GeoReg-CV"),
        ("官方AnyVisLoc工程", r"D:\GD\Benchmark"),
        ("Scene_01全量baseline", r"D:\GeoReg-CV\experiments\baseline_anyvisloc_scene01"),
        ("在线CDA单样本输出", r"D:\GeoReg-CV\outputs\online_cda"),
        ("在线单样本入口", r"D:\GeoReg-CV\pipelines\run_online_cda_sample.py"),
        ("方法与实验文档", r"D:\GeoReg-CV\docs"),
    ]
    add_table(document, ["内容", "位置"], locations)
    return document


if __name__ == "__main__":
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    build_document().save(OUTPUT)
    print(OUTPUT)
