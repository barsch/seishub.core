<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet exclude-result-prefixes="xlink" version="1.0"
    xmlns:xlink="http://www.w3.org/1999/xlink"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
    <xsl:output encoding="utf-8" indent="yes" media-type="text/xml"
        method="xml" />
    <xsl:template match="/">
        <xsl:text>&#10;</xsl:text>
        <html lang="en">
            <head>
                <title>Sales Results By Division</title>
            </head>
            <body>
                <table border="1">
                    <tr>
                        <th>Division</th>
                        <th>Revenue</th>
                        <th>Growth</th>
                        <th>Bonus</th>
                    </tr>
                    <xsl:for-each select="sales/division">
                        <!-- order the result by revenue -->
                        <xsl:sort data-type="number" order="descending"
                            select="revenue" />
                        <tr>
                            <td>
                                <em>
                                    <xsl:value-of select="@id" />
                                </em>
                            </td>
                            <td>
                                <xsl:value-of select="revenue" />
                            </td>
                            <td>
                                <!-- highlight negative growth in red -->
                                <xsl:if test="growth &lt; 0">
                                    <xsl:attribute name="style">
                                       <xsl:text>color:red</xsl:text>
                                    </xsl:attribute>
                                </xsl:if>
                                <xsl:value-of select="growth" />
                            </td>
                            <td>
                                <xsl:value-of select="bonus" />
                            </td>
                        </tr>
                    </xsl:for-each>
                </table>
            </body>
        </html>
    </xsl:template>
</xsl:stylesheet>
