package com.ravellosystems.hello;

/**
 * Hello world!
 *
 */
public class App 
{
    public static String hello()
    {
        return "Hello, world!";
    }

    public static String hello(String who)
    {
        return "Hello, " + who + "!";
    }

    public static void main( String[] args )
    {
        if (args.length >= 1)
            System.out.println(hello(args[0]));
        else
            System.out.println(hello());
    }
}
