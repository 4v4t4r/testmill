package com.ravellosystems.hello;

import junit.framework.Test;
import junit.framework.TestCase;
import junit.framework.TestSuite;

/**
 * Unit test for simple App.
 */
public class AppTest 
    extends TestCase
{
    /**
     * Create the test case
     *
     * @param testName name of the test case
     */
    public AppTest( String testName )
    {
        super( testName );
    }

    /**
     * @return the suite of tests being tested
     */
    public static Test suite()
    {
        return new TestSuite( AppTest.class );
    }

    /**
     * Tests
     */
    public void testDefaultGreeting()
    {
        assertEquals(App.hello(), "Hello, world!");
    }

    public void testCustomGreeting()
    {
        assertEquals(App.hello("Joe"), "Hello, Joe!");
    }
}
