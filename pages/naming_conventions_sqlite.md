title: naming-conventions-sqlite
date: 2024-08-08 10:20
author: Philipp Wagner
template: page
tags: sqlite, sql
summary: Naming Conventions for SQLite.

These are the Naming Conventions I am going to use SQLite databases. As far as I know, there 
are no best practices in SQLite, so you could come up with your own. These are the ones I am 
going to use, so everything is consistent.

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
              <td>Database File</td>
              <td>snake_case</td>
              <td>30</td>
              <td>No</td>
              <td>No</td>
              <td>.db</td>
              <td>
                  <code>my_database.db</code>
              </td>
          </tr>
          <tr>
              <td>Table Column</td>
              <td>snake_case</td>
              <td>128</td>
              <td>No</td>
              <td>No</td>
              <td>No</td>
              <td>
                  <code>my_column</code>
              </td>
          </tr>
          <tr>
              <td>Check Constraint</td>
              <td>snake_case</td>
              <td>128</td>
              <td>No</td>
              <td>
                  <code>ck_</code>
              </td>
              <td>No</td>
              <td>
                  <code>ck_table_description</code>
              </td>
          </tr>
          <tr>
              <td>Table Foreign Key</td>
              <td>snake_case</td>
              <td>128</td>
              <td>No</td>
              <td>
                  <code>fk_</code>
              </td>
              <td>No</td>
              <td>
                  <code>fk_source_colum_target_target_column</code>
              </td>
          </tr>
          <tr>
              <td>Table Index</td>
              <td>snake_case</td>
              <td>128</td>
              <td>No</td>
              <td>
                  <code>ix_</code>
              </td>
              <td>No</td>
              <td>
                  <code>ix_table_column_1_column_2</code>
              </td>
          </tr>
          <tr>
              <td>Table Unique Index</td>
              <td>snake_case</td>
              <td>128</td>
              <td>No</td>
              <td>
                  <code>ux_</code>
              </td>
              <td>No</td>
              <td>
                  <code>ux_table_columns</code>
              </td>
          </tr>
          <tr>
              <td>View</td>
              <td>snake_case</td>
              <td>128</td>
              <td>No</td>
              <td>
                  <code>vi_</code>
              </td>
              <td>No</td>
              <td>
                  <code>vi_viewname</code>
              </td>
          </tr>
      </tbody>
  </table>
</div>