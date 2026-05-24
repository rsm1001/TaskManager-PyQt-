"""
验证脚本 - 验证 data_manager 解耦后的功能是否正常
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """测试所有导入是否正常"""
    print("1. 测试导入模块...")
    try:
        from managers.data_manager import DataManager
        from managers.task_type import TaskType
        from services.service_factory import ServiceFactory
        from services.statistics_service import StatisticsService
        from services.search_service import SearchService
        from services.task_limit_service import TaskLimitService
        print("   [OK] 所有模块导入成功")
        return True
    except Exception as e:
        print(f"   [FAIL] 导入失败: {e}")
        return False

def test_task_type():
    """测试 TaskType 枚举"""
    print("2. 测试 TaskType 枚举...")
    try:
        from managers.task_type import TaskType
        assert TaskType.DAILY.value == "daily"
        assert TaskType.TODO.value == "todo"
        assert TaskType.ENTERTAINMENT.value == "entertainment"
        print("   [OK] TaskType 枚举正常")
        return True
    except Exception as e:
        print(f"   [FAIL] TaskType 测试失败: {e}")
        return False

def test_data_manager():
    """测试 DataManager 基本功能"""
    print("3. 测试 DataManager 基本功能...")
    try:
        from managers.data_manager import DataManager
        dm = DataManager()

        # 测试获取任务
        daily_tasks = dm.get_daily_tasks()
        todo_tasks = dm.get_todo_tasks()
        entertainment_tasks = dm.get_entertainment_tasks()
        print(f"   - 每日任务: {len(daily_tasks)} 个")
        print(f"   - 待办任务: {len(todo_tasks)} 个")
        print(f"   - 娱乐任务: {len(entertainment_tasks)} 个")

        # 测试统计功能
        stats = dm.get_statistics()
        print(f"   - 统计数据: {stats}")

        # 测试搜索功能
        results = dm.search_all_tasks("")
        assert isinstance(results, list)
        print(f"   - 搜索功能正常")

        # 测试任务限制服务
        limit_service = dm._get_task_limit_service()
        assert limit_service is not None
        print(f"   - 任务限制服务正常")

        # 测试统计服务
        stats_service = dm._get_statistics_service()
        assert stats_service is not None
        print(f"   - 统计服务正常")

        # 测试搜索服务
        search_service = dm._get_search_service()
        assert search_service is not None
        print(f"   - 搜索服务正常")

        dm.close_session()
        print("   [OK] DataManager 基本功能正常")
        return True
    except Exception as e:
        print(f"   [FAIL] DataManager 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_service_factory():
    """测试服务工厂单例模式"""
    print("4. 测试服务工厂单例模式...")
    try:
        from managers.data_manager import DataManager
        dm = DataManager()

        # 测试服务单例
        stats1 = dm._get_statistics_service()
        stats2 = dm._get_statistics_service()
        assert stats1 is stats2, "统计服务应该是单例"

        search1 = dm._get_search_service()
        search2 = dm._get_search_service()
        assert search1 is search2, "搜索服务应该是单例"

        limit1 = dm._get_task_limit_service()
        limit2 = dm._get_task_limit_service()
        assert limit1 is limit2, "任务限制服务应该是单例"

        dm.close_session()
        print("   [OK] 服务工厂单例模式正常")
        return True
    except Exception as e:
        print(f"   [FAIL] 服务工厂测试失败: {e}")
        return False

def main():
    print("=" * 50)
    print("开始验证 data_manager 解耦后的功能")
    print("=" * 50)

    results = []
    results.append(test_imports())
    results.append(test_task_type())
    results.append(test_data_manager())
    results.append(test_service_factory())

    print("=" * 50)
    if all(results):
        print("所有测试通过！验证成功。")
        return 0
    else:
        print("部分测试失败，请检查。")
        return 1

if __name__ == "__main__":
    sys.exit(main())
