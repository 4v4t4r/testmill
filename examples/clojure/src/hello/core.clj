(ns hello.core)

(defn hello
  ([] "Hello, world!")
  ([who] (str "Hello, " who "!")))

(defn -main [& args]
  (println
    (if args
      (hello (first args))
      (hello))))
