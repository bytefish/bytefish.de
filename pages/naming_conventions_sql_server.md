title: naming-conventions-sql-server
date: 2024-08-08 10:20
author: Philipp Wagner
template: page
tags: sqlserver, sql
summary: Naming Conventions for SQL Server.

These are the Naming Conventions I am usually using for SQL Server databases. I think it's a good idea to 
write them down somewhere... for copy and pasting into documentations. It's a good starting point I think.

<div class="table" style="font-size: 14px;">
  <table role="table" tabindex="0">
      <thead>
          <tr>
              <th>Object</th>
              <th>Notation</th>
              <th>Length</th>
              <th>Plural</th>
              <th>Prefix</th>
              <th>Suffix</th>
              <th>Example</th>
          </tr>
      </thead>
      <tbody>
          <tr>
              <td>Database</td>
              <td>PascalCase</td>
              <td>30</td>
              <td>No</td>
              <td>No</td>
              <td>No</td>
              <td>
                  <code>MyDatabase</code>
              </td>
          </tr>
          <tr>
              <td>Schema</td>
              <td>PascalCase</td>
              <td>30</td>
              <td>No</td>
              <td>No</td>
              <td>No</td>
              <td>
                  <code>MySchema</code>
              </td>
          </tr>
          <tr>
              <td>Global Temporary Table</td>
              <td>PascalCase</td>
              <td>117</td>
              <td>No</td>
              <td>No</td>
              <td>No</td>
              <td>
                  <code>##MyTable</code>
              </td>
          </tr>
          <tr>
              <td>Local Temporary Table</td>
              <td>PascalCase</td>
              <td>116</td>
              <td>No</td>
              <td>No</td>
              <td>No</td>
              <td>
                  <code>#MyTable</code>
              </td>
          </tr>
          <tr>
              <td>File Table</td>
              <td>PascalCase</td>
              <td>128</td>
              <td>No</td>
              <td>
                  <code>FT_</code>
              </td>
              <td>No</td>
              <td>
                  <code>FT_MyTable</code>
              </td>
          </tr>
          <tr>
              <td>Temporal Table</td>
              <td>PascalCase</td>
              <td>128</td>
              <td>No</td>
              <td>No</td>
              <td>
                  <code>History</code>
              </td>
              <td>
                  <code>MyTableHistory</code>
              </td>
          </tr>
          <tr>
              <td>Table Column</td>
              <td>PascalCase</td>
              <td>128</td>
              <td>No</td>
              <td>No</td>
              <td>No</td>
              <td>
                  <code>MyColumn</code>
              </td>
          </tr>
          <tr>
              <td>Columns Check Constraint</td>
              <td>PascalCase</td>
              <td>128</td>
              <td>No</td>
              <td>
                  <code>CTK_</code>
              </td>
              <td>No</td>
              <td>
                  <code>CTK_MyTable_MyColumn_AnotherColumn</code>
              </td>
          </tr>
          <tr>
              <td>Column Check Constraint</td>
              <td>PascalCase</td>
              <td>128</td>
              <td>No</td>
              <td>
                  <code>CK_</code>
              </td>
              <td>No</td>
              <td>
                  <code>CK_MyTable_MyColumn</code>
              </td>
          </tr>
          <tr>
              <td>Column Default Values</td>
              <td>PascalCase</td>
              <td>128</td>
              <td>No</td>
              <td>
                  <code>DF_</code>
              </td>
              <td>No</td>
              <td>
                  <code>DF_MyTable_MyColumn</code>
              </td>
          </tr>
          <tr>
              <td>Table Primary Key</td>
              <td>PascalCase</td>
              <td>128</td>
              <td>No</td>
              <td>
                  <code>PK_</code>
              </td>
              <td>No</td>
              <td>
                  <code>PK_MyTable</code>
              </td>
          </tr>
          <tr>
              <td>Table Unique (Alternative) Key</td>
              <td>PascalCase</td>
              <td>128</td>
              <td>No</td>
              <td>
                  <code>AK_</code>
              </td>
              <td>No</td>
              <td>
                  <code>AK_MyTable_MyColumn_AnotherColumn</code>
              </td>
          </tr>
          <tr>
              <td>Table Foreign Key</td>
              <td>PascalCase</td>
              <td>128</td>
              <td>No</td>
              <td>
                  <code>FK_</code>
              </td>
              <td>No</td>
              <td>
                  <code>FK_MyTable_MyColumn_ReferencedTable_ReferencedColumn</code>
              </td>
          </tr>
          <tr>
              <td>Table Clustered Index</td>
              <td>PascalCase</td>
              <td>128</td>
              <td>No</td>
              <td>
                  <code>IXC_</code>
              </td>
              <td>No</td>
              <td>
                  <code>IXC_MyTable_MyColumn_AnotherColumn</code>
              </td>
          </tr>
          <tr>
              <td>Table Non Clustered Index</td>
              <td>PascalCase</td>
              <td>128</td>
              <td>No</td>
              <td>
                  <code>IX_</code>
              </td>
              <td>No</td>
              <td>
                  <code>IX_MyTable_MyColumn_AnotherColumn</code>
              </td>
          </tr>
          <tr>
              <td>Table Unique Index</td>
              <td>PascalCase</td>
              <td>128</td>
              <td>No</td>
              <td>
                  <code>UX_</code>
              </td>
              <td>No</td>
              <td>
                  <code>UX_MyTable_MyColumn_AnotherColumn</code>
              </td>
          </tr>
          <tr>
              <td>DDL Trigger</td>
              <td>PascalCase</td>
              <td>128</td>
              <td>No</td>
              <td>
                  <code>TR_</code>
              </td>
              <td>
                  <code>_DDL</code>
              </td>
              <td>
                  <code>TR_LogicalName_DDL</code>
              </td>
          </tr>
          <tr>
              <td>DML Trigger</td>
              <td>PascalCase</td>
              <td>128</td>
              <td>No</td>
              <td>
                  <code>TR_</code>
              </td>
              <td>
                  <code>_DML</code>
              </td>
              <td>
                  <code>TR_MyTable_LogicalName_DML</code>
              </td>
          </tr>
          <tr>
              <td>Logon Trigger</td>
              <td>PascalCase</td>
              <td>128</td>
              <td>No</td>
              <td>
                  <code>TR_</code>
              </td>
              <td>
                  <code>_LOG</code>
              </td>
              <td>
                  <code>TR_LogicalName_LOG</code>
              </td>
          </tr>
          <tr>
              <td>View</td>
              <td>PascalCase</td>
              <td>128</td>
              <td>No</td>
              <td>
                  <code>VI_</code>
              </td>
              <td>No</td>
              <td>
                  <code>VI_LogicalName</code>
              </td>
          </tr>
          <tr>
              <td>Indexed View</td>
              <td>PascalCase</td>
              <td>128</td>
              <td>No</td>
              <td>
                  <code>VIX_</code>
              </td>
              <td>No</td>
              <td>
                  <code>VIX_LogicalName</code>
              </td>
          </tr>
          <tr>
              <td>Statistic</td>
              <td>PascalCase</td>
              <td>128</td>
              <td>No</td>
              <td>
                  <code>ST_</code>
              </td>
              <td>No</td>
              <td>
                  <code>ST_MyTable_MyColumn_AnotherColumn</code>
              </td>
          </tr>
          <tr>
              <td>Stored Procedure</td>
              <td>PascalCase</td>
              <td>128</td>
              <td>No</td>
              <td>
                  <code>usp_</code>
              </td>
              <td>No</td>
              <td>
                  <code>usp_LogicalName</code>
              </td>
          </tr>
          <tr>
              <td>Scalar User-Defined Function</td>
              <td>PascalCase</td>
              <td>128</td>
              <td>No</td>
              <td>
                  <code>udf_</code>
              </td>
              <td>No</td>
              <td>
                  <code>udf_FunctionLogicalName</code>
              </td>
          </tr>
          <tr>
              <td>Table-Valued Function</td>
              <td>PascalCase</td>
              <td>128</td>
              <td>No</td>
              <td>
                  <code>tvf_</code>
              </td>
              <td>No</td>
              <td>
                  <code>tvf_FunctionLogicalName</code>
              </td>
          </tr>
          <tr>
              <td>Sequence</td>
              <td>PascalCase</td>
              <td>128</td>
              <td>No</td>
              <td>
                  <code>sq_</code>
              </td>
              <td>No</td>
              <td>
                  <code>sq_TableName</code>
              </td>
          </tr>
      </tbody>
  </table>
</div>