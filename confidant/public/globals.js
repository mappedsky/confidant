import _ from 'lodash';
import $ from 'jquery';
import angular from 'angular';
import { Spinner } from 'spin.js';

window._ = _;
window.$ = $;
window.jQuery = $;
window.Spinner = Spinner;

if (!window.angular) {
    window.angular = angular;
}
