(ns hello.core-test
  (:use clojure.test
        hello.core))

(deftest test-default
  (testing "Default greeting"
    (is (= (hello) "Hello, world!")))
  (testing "Customized greeting"
    (is (= (hello "Joe") "Hello, Joe!"))))
