import sys
from media_processors import TemplateProcessor

def load_processor(name):
    (module_name, _ , processor) = name.rpartition(".")
    __import__(module_name)
    module = sys.modules[module_name]
    return getattr(module, processor)

class Processor(object):
    def __init__(self, settings):
        self.settings = settings 
        self.processor_cache = {}
        
    def get_node_processors(self, node):
        if node.fragment in self.processor_cache:
            return self.processor_cache[node.fragment]
        
        processors = {}
        if node.type == "media":
            processors = self.settings.MEDIA_PROCESSORS
        elif node.type == "content":
            processors = self.settings.CONTENT_PROCESSORS
        else:
            return []
        return self.extract_processors(node, processors, self.processor_cache)

        
    def extract_processors(self, node, processors, cache):
        current_processors = []
        this_node = node
        while this_node:
            fragment = this_node.fragment
            if fragment in processors:
                current_processors.append(processors[fragment])
            this_node = this_node.parent
        # Add the default processors to the list
        if "*" in processors:
            current_processors.append(processors["*"])
        cache[node.fragment] = current_processors
        current_processors.reverse()
        return current_processors
                
    def process(self, resource):
        if (resource.node.type not in ("content", "media") or
            resource.is_layout):
            return
        processor_config = self.get_node_processors(resource.node)
        processors = []
        for processer_map in processor_config:
            if resource.file.extension in processer_map:
                processors.extend(processer_map[resource.file.extension])
        resource.temp_file.parent.make()        
        resource.source_file.copy_to(resource.temp_file)  
        (original_source, resource.source_file) = (
                                resource.source_file, resource.temp_file)
        for processor_name in processors:
            processor = load_processor(processor_name)
            processor.process(resource)
        
        if resource.node.type == "content":
            self.settings.CONTEXT['page'] = resource
            TemplateProcessor.process(resource)
            self.settings.CONTEXT['page'] = None
            
        resource.source_file = original_source
          
    def post_process(self, node):
        for child in node.walk():
            if not child.type in ("content", "media"):
                continue
            fragment = child.temp_folder.get_fragment(node.site.temp_folder)
            fragment = fragment.rstrip("/")
            if fragment in self.settings.SITE_POST_PROCESSORS:
                processor_config = self.settings.SITE_POST_PROCESSORS[fragment]
                for processor_name, params in processor_config.iteritems():
                    processor = load_processor(processor_name)
                    processor.process(child.temp_folder, params)