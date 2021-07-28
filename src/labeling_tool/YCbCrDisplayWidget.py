from textwrap import dedent

from PySide6 import QtGui as qtg
from PySide6 import QtOpenGLWidgets as qglw
from PySide6 import QtOpenGL as qgl
from OpenGL import GL


class YCbCrDisplayWidget(qglw.QOpenGLWidget):
    """Widget for display YUV420p frames

    Internally, the widget uses OpenGL shaders to convert YUV420p to RGB space.
    Performance should be better than doing the conversion in software.
    """

    # Vertex shader source
    _vtx_shader_src = dedent("""
    #version 130

    // Position of vertex
    in vec2 posIn;
    // Texture coordinates for the vertex
    in vec2 texPosIn;

    // To forward texture coordinates to fragment shader
    out vec2 texPos;

    void main() {
        texPos = texPosIn;
        gl_Position = vec4(posIn, 0.0, 1.0);
    }
    """)

    # Fragment shader source
    _frag_shader_src = dedent("""
    #version 130

    // Get texture coordinates from the vertex shader
    in vec2 texPos;

    out vec4 fragColor;

    // 3x3 colorspace conversion matrix to transform YUV color to RGB space
    // Different standards suggest different matrices
    // uniform mat3 cs_matrix;
    const mat3 cs_matrix = mat3(
        1       ,  1       ,  1       ,
        0       , -0.18732 ,  1.8556 ,
        1.5748 , -0.46812 ,  0
    );

    // Y plane of frame (full resolution, 8 bits)
    uniform sampler2D tex_y;
    // Cb plane of frame (quarter resolution, 8 bits)
    uniform sampler2D tex_cb;
    // Cr plane of frame (quarter resolution, 8 bits)
    uniform sampler2D tex_cr;

    void main() {
        vec3 yuv;
        vec3 rgb;

        yuv.x = texture(tex_y, texPos).r;
        // Offset chroma channels to between -0.5 to 0.5 for colorspace conversion
        yuv.y = texture(tex_cb, texPos).r - 0.5;
        yuv.z = texture(tex_cr, texPos).r - 0.5;

        rgb = cs_matrix * yuv;
        fragColor = vec4(rgb, 1.0);
    }
    """)


    # Vertex data contains positions of our rectangle and corresponding
    # texture coordinates
    _vertices = [
        # position_x, position_y, texture_s, texture_t
                -1.0,        1.0,       0.0,       0.0, # 0
                 1.0,        1.0,       1.0,       0.0, # 1
                -1.0,       -1.0,       0.0,       1.0, # 2
                 1.0,       -1.0,       1.0,       1.0  # 3
    ]


    # Indices to draw a rectangle with TRIANGLES_STRIP
    _indices = [
        0, 1, 2, 3
    ]

    _bt709_transform_rgb = [

    ]

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        # Request OpenGL 3.0 Core Profile context
        fmt = qtg.QSurfaceFormat()
        fmt.setRenderableType(qtg.QSurfaceFormat.RenderableType.OpenGL)

        self._profile = qgl.QOpenGLVersionProfile()
        self._profile.setVersion(3, 0)
        self._profile.setProfile(qtg.QSurfaceFormat.OpenGLContextProfile.CoreProfile)

        # Make it explicit that we need OpenGL 3.0 Core context
        fmt.setVersion(*self._profile.version())
        fmt.setProfile(self._profile.profile())
        self.setFormat(fmt)

        self._program = None
        self._vao = None
        self._buff_vertices = None
        self._buff_indices = None

        self._tex_y = None
        self._tex_cb = None
        self._tex_cr = None

        self._media_path = None

        self.width = -1
        self.height = -1

    def _compile_gl(self):
        self._program = GL.glCreateProgram()

        vtx_shader = GL.glCreateShader(GL.GL_VERTEX_SHADER)
        self._compile_shader(vtx_shader, self._vtx_shader_src)
        frag_shader = GL.glCreateShader(GL.GL_FRAGMENT_SHADER)
        self._compile_shader(frag_shader, self._frag_shader_src)

        GL.glAttachShader(self._program, vtx_shader)
        GL.glAttachShader(self._program, frag_shader)

        GL.glBindAttribLocation(self._program, 0, 'posIn')
        GL.glBindAttribLocation(self._program, 1, 'texPosIn')

        self._link_program(self._program)

        GL.glDeleteShader(vtx_shader)
        GL.glDeleteShader(frag_shader)

    def _init_gl_buffers(self):
        self._tex_y = GL.glGenTextures(1)
        # Luma texture (Y)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self._tex_y)
        # Wrapping behavior
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_S, GL.GL_CLAMP_TO_EDGE)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_T, GL.GL_CLAMP_TO_EDGE)
        # Resizing behavior
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)

        # Chroma textures (both Cb and Cr)
        self._tex_cb, self._tex_cr = GL.glGenTextures(2)
        for tex in [self._tex_cb, self._tex_cr]:
            GL.glBindTexture(GL.GL_TEXTURE_2D, tex)
            # Wrapping behavior
            GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_S, GL.GL_CLAMP_TO_EDGE)
            GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_T, GL.GL_CLAMP_TO_EDGE)
            # Resizing behavior
            GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR)
            GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)

        self._vao = GL.glGenVertexArrays(1)
        GL.glBindVertexArray(self._vao)

        self._buff_vertices, self._buff_indices = GL.glGenBuffers(2)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self._buff_vertices)
        data = (GL.GLfloat * len(self._vertices))(*self._vertices)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, GL.sizeof(data), data, GL.GL_STATIC_DRAW)

        GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, self._buff_indices)
        indices = (GL.GLubyte * len(self._indices))(*self._indices)
        GL.glBufferData(GL.GL_ELEMENT_ARRAY_BUFFER, GL.sizeof(indices), indices, GL.GL_STATIC_DRAW)

        float_size = GL.sizeof(GL.GLfloat)

        GL.glVertexAttribPointer(0, 2, GL.GL_FLOAT, GL.GL_FALSE, 4 * float_size, GL.GLvoidp(0))
        GL.glVertexAttribPointer(1, 2, GL.GL_FLOAT, GL.GL_FALSE, 4 * float_size, GL.GLvoidp(2 * float_size))
        GL.glEnableVertexAttribArray(0)
        GL.glEnableVertexAttribArray(1)

    @staticmethod
    def _compile_shader(shader, shader_source: str, encoding='utf-8'):
        """Compile the shader against the given source
        """
        GL.glShaderSource(shader, [ shader_source.encode(encoding) ])
        GL.glCompileShader(shader)
        compile_status = GL.glGetShaderiv(shader, GL.GL_COMPILE_STATUS)
        if compile_status != GL.GL_TRUE:
            # Compilation failed
            log = GL.glGetShaderInfoLog(shader)
            raise ValueError(f'ERROR: Shader compilation failed\n\n{log}')

    @staticmethod
    def _link_program(program):
        GL.glLinkProgram(program)
        link_status = GL.glGetProgramiv(program, GL.GL_LINK_STATUS)
        if link_status != GL.GL_TRUE:
            # Linking failed
            log = GL.glGetProgramInfoLog(program)
            raise ValueError(f'ERROR: Program linking failed\n\n{log}')

    def initializeGL(self):
        """Set up any required OpenGL resources and state

        Called once before the first time resizeGL() or paintGL() is called.
        The rendering context has already been made current before this
        function is called. Note however that the framebuffer is not yet
        available at this stage, so avoid issuing draw calls from here. Defer
         such calls to paintGL() instead.
        """
        # Get the OpenGL functions appropriate to our current context
        self.context().aboutToBeDestroyed.connect(self.cleanup)
        self._compile_gl()
        self._init_gl_buffers()

        GL.glClearColor(0.0, 0.0, 0.0, 1.0)
        # Set uniforms (must 'use' program before setting)
        GL.glUseProgram(self._program)

        # uni_loc = GL.glGetUniformLocation(self._program, 'cs_matrix')
        # GL.glUniformMatrix3fv()

        # Assign texture units 0, 1 and 2 to Y, Cb and Cr textures
        for i, tex_name in enumerate(['tex_y', 'tex_cb', 'tex_cr']):
            tex_loc = GL.glGetUniformLocation(self._program, tex_name)
            GL.glUniform1i(tex_loc, i)


    def paintGL(self):
        """Paint the scene using OpenGL functions

        The rendering context has already been made current before this
        function is called. The framebuffer is also bound and the viewport is
        set up by a call to glViewport()
        """
        GL.glClear(GL.GL_COLOR_BUFFER_BIT)

        GL.glUseProgram(self._program)
        GL.glBindVertexArray(self._vao)

        GL.glDrawElements(GL.GL_TRIANGLE_STRIP, 4, GL.GL_UNSIGNED_BYTE, GL.GLvoidp(0))

    def resizeGL(self, width: int, height: int):
        """Called whenever the widget has been resized

        The rendering context has already been made current before this
        function is called. The framebuffer is also bound.
        """
        GL.glViewport(0, 0, width, height)

    def cleanup(self):
        # Must make context current before using OpenGL API
        self.makeCurrent()

        GL.glDeleteTextures([self._tex_y, self._tex_cb, self._tex_cr])
        self._tex_y, self._tex_cb, self._tex_cr = [None] * 3

        GL.glDeleteBuffers([self._buff_vertices, self._buff_indices])
        self._buff_vertices = None
        self._buff_indices = None

        GL.glDeleteVertexArrays(self._vao)
        self._vao = None

        GL.glDeleteProgram(self._program)
        self._program = None

        self.doneCurrent()

    def refresh_frame(self, y, cb, cr):
        self.makeCurrent()

        if self.width < 0 or self.height < 0:
            self.height, self.width = y.shape

            GL.glActiveTexture(GL.GL_TEXTURE0)
            GL.glBindTexture(GL.GL_TEXTURE_2D, self._tex_y)
            GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RED, self.width, self.height, 0, GL.GL_RED, GL.GL_UNSIGNED_BYTE, None)

            for i, tex in enumerate([self._tex_cb, self._tex_cr], start=1):
                GL.glActiveTexture(GL.GL_TEXTURE0 + i)
                GL.glBindTexture(GL.GL_TEXTURE_2D, tex)
                GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RED, self.width // 2, self.height // 2, 0, GL.GL_RED, GL.GL_UNSIGNED_BYTE, None)


        GL.glActiveTexture(GL.GL_TEXTURE0)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self._tex_y)
        GL.glTexSubImage2D(GL.GL_TEXTURE_2D, 0, 0, 0, self.width, self.height, GL.GL_RED, GL.GL_UNSIGNED_BYTE, y)
        GL.glActiveTexture(GL.GL_TEXTURE1)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self._tex_cb)
        GL.glTexSubImage2D(GL.GL_TEXTURE_2D, 0, 0, 0, self.width // 2, self.height // 2, GL.GL_RED, GL.GL_UNSIGNED_BYTE, cb)
        GL.glActiveTexture(GL.GL_TEXTURE2)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self._tex_cr)
        GL.glTexSubImage2D(GL.GL_TEXTURE_2D, 0, 0, 0, self.width // 2, self.height // 2, GL.GL_RED, GL.GL_UNSIGNED_BYTE, cr)

        self.doneCurrent()
