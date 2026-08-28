"""Deterministic, scenario-rich demo data for local Agent evaluation."""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


SHANGHAI = ZoneInfo("Asia/Shanghai")


CAMPUS_DATA = (
    ("pudong", "浦东校区", "上海市浦东新区张江路 88 号"),
    ("xuhui", "徐汇校区", "上海市徐汇区漕溪北路 120 号"),
    ("yangpu", "杨浦校区", "上海市杨浦区淞沪路 168 号"),
    ("minhang", "闵行校区", "上海市闵行区莘松路 58 号"),
    ("jingan", "静安校区", "上海市静安区共和新路 2188 号"),
)


COURSE_DATA = (
    ("math_j2", "初二数学提升", "数学", "初二", 90, "代数、几何与校内同步提升"),
    ("math_j3", "初三数学冲刺", "数学", "初三", 90, "中考专题、压轴题与错题复盘"),
    ("math_h1", "高一数学衔接", "数学", "高一", 90, "函数、集合与高中数学思维衔接"),
    ("english_g6", "六年级英语基础", "英语", "六年级", 60, "词汇、语法与口语基础训练"),
    ("english_h1", "高一英语强化", "英语", "高一", 90, "阅读、语法与写作综合训练"),
    ("physics_j2", "初二物理启蒙", "物理", "初二", 90, "力学入门、实验方法与概念理解"),
    ("physics_j3", "初三物理冲刺", "物理", "初三", 90, "中考物理专题与实验题强化"),
    ("chemistry_j3", "初三化学入门", "化学", "初三", 90, "基础概念、方程式与实验现象"),
    ("chinese_g5", "五年级语文阅读", "语文", "五年级", 60, "阅读理解、表达与写作素材积累"),
    ("physics_h2", "高二物理专题", "物理", "高二", 120, "电磁学、动量与综合题训练"),
)


STUDENT_DATA = (
    ("小明", "初二"),
    ("小雨", "初二"),
    ("婷婷", "高一"),
    ("小宇", "初二"),
    ("安安", "初三"),
    ("乐乐", "五年级"),
    ("子轩", "高一"),
    ("浩然", "高二"),
    ("欣怡", "高一"),
    ("可可", "六年级"),
    ("天佑", "初三"),
    ("若曦", "高一"),
    ("晨晨", "初三"),
    ("果果", "五年级"),
    ("文博", "初二"),
    ("思琪", "高二"),
    ("嘉豪", "初三"),
    ("语桐", "六年级"),
)


TEACHER_DATA = (
    ("wang", "王老师", "八年初中数学教学经验", "初中数学、几何", ("math_j2", "math_j3"), ("pudong", "xuhui"), 270),
    ("li", "李老师", "擅长分层教学与学习规划", "初中数学、英语基础", ("math_j2", "math_j3", "english_g6"), ("pudong", "xuhui", "yangpu"), 360),
    ("zhang", "张老师", "高中英语教研教师", "高中英语、写作", ("english_g6", "english_h1"), ("xuhui", "jingan"), 360),
    ("chen", "陈老师", "物理实验与竞赛辅导经验", "初中物理、实验", ("physics_j2", "physics_j3"), ("pudong", "yangpu"), 300),
    ("liu", "刘老师", "中考化学备考教师", "初中化学、实验", ("chemistry_j3",), ("xuhui", "minhang"), 300),
    ("zhao", "赵老师", "小学语文阅读写作教师", "小学语文、阅读写作", ("chinese_g5",), ("yangpu", "jingan"), 300),
    ("zhou", "周老师", "高中数学教研组教师，周末兼职", "高中数学、函数", ("math_h1",), ("xuhui", "jingan"), 90),
    ("wu", "吴老师", "十年中高考物理教学经验", "初高中物理、电磁学", ("physics_j3", "physics_h2"), ("pudong", "minhang"), 360),
    ("sun", "孙老师", "数学竞赛与校内培优教师", "初高中数学、竞赛", ("math_j2", "math_j3", "math_h1"), ("yangpu", "minhang"), 360),
    ("zheng", "郑老师", "双语教学与口语训练教师", "英语、口语、写作", ("english_g6", "english_h1"), ("pudong", "minhang"), 300),
    ("huang", "黄老师", "理化跨学科教研教师", "物理、化学、实验", ("physics_j2", "physics_j3", "chemistry_j3"), ("yangpu", "jingan"), 360),
    ("he", "何老师", "专注学习习惯与阅读能力培养", "小学语文、学习规划", ("chinese_g5",), ("pudong", "xuhui"), 300),
    ("gao", "高老师", "高中数学竞赛教练", "高中数学、函数、竞赛", ("math_j3", "math_h1"), ("xuhui", "jingan"), 360),
    ("lin", "林老师", "高考英语阅读写作专项教师", "高中英语、阅读、写作", ("english_g6", "english_h1"), ("xuhui", "yangpu"), 360),
    ("xu", "徐老师", "初高中物理衔接课程教师", "初高中物理、力学", ("physics_j2", "physics_h2"), ("minhang", "pudong"), 360),
)


BOOKING_DATA = (
    ("小雨", "wang", "math_j2", "pudong", 1, 14, "confirmed", "指定教师冲突演示"),
    ("小明", "li", "math_j2", "pudong", 1, 16, "confirmed", "常规数学提升课"),
    ("婷婷", "zhang", "english_h1", "xuhui", 1, 18, "pending", "等待家长确认"),
    ("小宇", "chen", "physics_j2", "pudong", 2, 10, "confirmed", "物理启蒙体验课"),
    ("安安", "liu", "chemistry_j3", "minhang", 2, 14, "confirmed", "中考化学专题"),
    ("乐乐", "zhao", "chinese_g5", "yangpu", 3, 15, "confirmed", "阅读理解训练"),
    ("子轩", "zhou", "math_h1", "jingan", 3, 18, "confirmed", "教师每日上限演示"),
    ("浩然", "wu", "physics_h2", "minhang", 4, 10, "cancelled", "家长提前取消"),
    ("欣怡", "sun", "math_h1", "yangpu", 4, 14, "confirmed", "函数专题训练"),
    ("可可", "zheng", "english_g6", "pudong", 5, 16, "pending", "等待确认教材版本"),
    ("天佑", "huang", "physics_j3", "yangpu", 6, 9, "confirmed", "中考实验题训练"),
    ("若曦", "lin", "english_h1", "xuhui", 6, 14, "confirmed", "高考阅读写作"),
)


KNOWLEDGE_DATA = (
    ("浦东校区位于张江路 88 号，提供初中数学、英语和物理一对一课程。", "campus", ["浦东校区", "张江", "地址"]),
    ("徐汇校区位于漕溪北路 120 号，重点提供高中数学、英语和理化课程。", "campus", ["徐汇校区", "漕溪北路", "地址"]),
    ("杨浦校区位于淞沪路 168 号，设有数学、物理、化学和小学语文课程。", "campus", ["杨浦校区", "淞沪路", "地址"]),
    ("闵行校区位于莘松路 58 号，提供初高中数学、英语及理化课程。", "campus", ["闵行校区", "莘松路", "地址"]),
    ("静安校区位于共和新路 2188 号，提供高中精品小班和一对一课程。", "campus", ["静安校区", "共和新路", "地址"]),
    ("课程开始前 24 小时可免费取消或改期；不足 24 小时请联系教务协调。", "policy", ["取消", "改期", "24小时"]),
    ("学生请假后可在 30 天内申请一次补课，补课时间需根据教师档期重新安排。", "policy", ["请假", "补课", "政策"]),
    ("跨校区调整课程需至少提前 48 小时申请，教务会重新核验教师服务校区与档期。", "policy", ["跨校区", "调整", "48小时"]),
    ("初二数学提升课覆盖代数、几何和校内同步复习，默认每次 90 分钟。", "course", ["初二", "数学", "课程"]),
    ("高一英语强化课覆盖阅读、语法与写作，默认每次 90 分钟。", "course", ["高一", "英语", "课程"]),
    ("五年级语文阅读课以阅读理解、表达和写作素材积累为主，每次 60 分钟。", "course", ["五年级", "语文", "阅读"]),
    ("教师推荐会综合课程资质、服务校区、可用档期、学生偏好和当日课时负载。", "teacher", ["教师推荐", "匹配", "资质", "档期"]),
)


def _local_day(reference_time: datetime | None) -> datetime:
    current = reference_time or datetime.now(SHANGHAI)
    if current.tzinfo is None or current.utcoffset() is None:
        raise ValueError("reference_time must include a timezone")
    return current.astimezone(SHANGHAI).replace(hour=0, minute=0, second=0, microsecond=0)


def seed_demo_data(repository, *, reference_time: datetime | None = None) -> None:
    """Seed an empty database once with a reproducible operating scenario."""

    if repository.list_campuses():
        return

    base_day = _local_day(reference_time)
    campuses = {
        key: repository.create_campus(name, address)
        for key, name, address in CAMPUS_DATA
    }
    courses = {
        key: repository.create_course(name, subject, grade, duration, description)
        for key, name, subject, grade, duration, description in COURSE_DATA
    }
    students = {
        name: repository.create_student(name, grade, f"demo-{index:03d}")
        for index, (name, grade) in enumerate(STUDENT_DATA, start=1)
    }

    teachers = {}
    for key, name, bio, specialties, course_keys, campus_keys, max_daily_minutes in TEACHER_DATA:
        teacher = repository.create_teacher(name, bio, specialties)
        if max_daily_minutes != teacher.max_daily_minutes:
            teacher = repository.update_teacher(teacher.id, max_daily_minutes=max_daily_minutes)
        teachers[key] = teacher
        for course_key in course_keys:
            repository.qualify_teacher(teacher.id, courses[course_key].id)
        for campus_key in campus_keys:
            repository.assign_teacher_to_campus(teacher.id, campuses[campus_key].id)
        for day_offset in range(14):
            day = base_day + timedelta(days=day_offset)
            repository.add_teacher_availability(
                teacher.id,
                day.replace(hour=9),
                day.replace(hour=21),
            )

    repository.set_student_preferred_teacher(students["小明"].id, teachers["wang"].id)
    repository.set_student_preferred_teacher(students["婷婷"].id, teachers["zhang"].id)

    for student_name, teacher_key, course_key, campus_key, day_offset, hour, status, notes in BOOKING_DATA:
        course = courses[course_key]
        start_at = (base_day + timedelta(days=day_offset)).replace(hour=hour)
        repository.create_booking(
            student_id=students[student_name].id,
            teacher_id=teachers[teacher_key].id,
            course_id=course.id,
            campus_id=campuses[campus_key].id,
            start_at=start_at,
            end_at=start_at + timedelta(minutes=course.duration_minutes),
            status=status,
            notes=notes,
        )

    for content, category, keywords in KNOWLEDGE_DATA:
        repository.add_knowledge(content, category, keywords)
