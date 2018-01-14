// Sass configuration
var gulp = require('gulp');
var sass = require('gulp-sass');

gulp.task('sass', function() {
    gulp.src('src/*.scss')
        .pipe(sass())
        .pipe(gulp.dest('src/static/css'))
});

gulp.task('default', ['sass']);