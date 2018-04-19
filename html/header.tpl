<!DOCTYPE html>
<html>
<head>
   <meta name="viewport" content="width=device-width, initial-scale=1">
   <link rel="stylesheet" href="http://code.jquery.com/mobile/1.4.2/jquery.mobile-1.4.2.min.css">
   <script src="http://code.jquery.com/jquery-1.10.2.min.js"></script>
   <script src="http://code.jquery.com/mobile/1.4.2/jquery.mobile-1.4.2.min.js"></script>
   <title>PIAB: {{title}}</title>
</head>
<body>
   <div data-role="page">
      <div data-role="navbar">
	 <ul>
	    <li><a href="/" data-icon="home" data-transition="none" \\
            % if title == 'Home':
            class="ui-btn-active"
            % end
            >Home</a></li>
	    <li><a href="/config" data-icon="gear" data-transition="none" \\
            % if title == 'Configuration':
            class="ui-btn-active"
            % end
            >Configuration</a></li>
	 </ul>
      </div><!-- /navbar -->
      <div data-role="main" class="ui-content">
