from agents.task_classification_agent import TaskClassificationAgent


def test_classifier_distinguishes_booking_from_approximate_price_question():
    classifier = TaskClassificationAgent()

    assert classifier.classify("给小明在浦东校区约初二数学") == "scheduling"
    assert classifier.classify("这个课程大约多少钱") == "consultation"
    assert classifier.classify("今天天气怎么样") == "unrelated"
